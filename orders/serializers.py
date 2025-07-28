from rest_framework import serializers
from django.utils import timezone
from .models import Order, OrderLine, OrderStatusHistory, Receipt
from customers.serializers import CustomerListSerializer
from services.serializers import ServiceListSerializer
from system_settings.models import PaymentMethod


class OrderLineSerializer(serializers.ModelSerializer):
    """Serializer for OrderLine model"""
    service_name = serializers.CharField(source='service.name', read_only=True)
    service_category = serializers.CharField(source='service.category.name', read_only=True)
    
    class Meta:
        model = OrderLine
        fields = [
            'id', 'service', 'service_name', 'service_category',
            'pieces', 'unit_price', 'line_total', 'notes'
        ]
        read_only_fields = ['id', 'unit_price', 'line_total']
    
    def validate_pieces(self, value):
        """Validate pieces is positive"""
        if value < 1:
            raise serializers.ValidationError("Number of pieces must be at least 1")
        return value


class OrderLineCreateSerializer(OrderLineSerializer):
    """Serializer for creating order lines"""
    
    def create(self, validated_data):
        """Create order line with calculated pricing"""
        service = validated_data['service']
        pieces = validated_data['pieces']
        
        # Calculate pricing from service
        validated_data['unit_price'] = service.unit_price
        validated_data['line_total'] = service.calculate_total(pieces)
        
        return super().create(validated_data)


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for Order model"""
    lines = OrderLineSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    customer_phone = serializers.CharField(source='customer.phone', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    payment_method_name = serializers.CharField(source='payment_method.name', read_only=True)
    total_pieces = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'uuid', 'customer', 'customer_name', 'customer_phone',
            'created_by', 'created_by_name', 'status', 'payment_method', 'payment_method_name',
            'subtotal', 'discount_percentage', 'discount_amount', 'total_amount',
            'expected_completion', 'completed_at', 'delivered_at',
            'notes', 'special_instructions', 'lines', 'total_pieces',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'order_number', 'uuid', 'subtotal', 'discount_amount', 
            'total_amount', 'completed_at', 'delivered_at', 'created_at', 'updated_at'
        ]
    
    def validate_discount_percentage(self, value):
        """Validate discount percentage"""
        if value < 0 or value > 100:
            raise serializers.ValidationError("Discount percentage must be between 0 and 100")
        return value


class OrderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating orders with order lines"""
    lines = OrderLineCreateSerializer(many=True, write_only=True)
    payment_method = serializers.CharField(write_only=True, help_text="Payment method code")
    
    class Meta:
        model = Order
        fields = [
            'customer', 'payment_method', 'discount_percentage',
            'expected_completion', 'notes', 'special_instructions', 'lines'
        ]
    
    def validate_payment_method(self, value):
        """Validate payment method exists and is active"""
        try:
            payment_method = PaymentMethod.objects.get(code=value, is_active=True)
            return payment_method
        except PaymentMethod.DoesNotExist:
            raise serializers.ValidationError(f"Payment method '{value}' not found or inactive")
    
    def create(self, validated_data):
        """Create order with lines"""
        lines_data = validated_data.pop('lines')
        validated_data['created_by'] = self.context['request'].user
        
        # Create order first (without calculating totals)
        order = Order(**validated_data)
        order.save(skip_calculation=True)  # Skip calculation on first save
        
        # Create order lines
        for line_data in lines_data:
            OrderLine.objects.create(order=order, **line_data)
        
        # Now recalculate totals and save again
        order.calculate_totals()
        order.save()
        
        # Update customer stats
        order.customer.total_orders += 1
        order.customer.total_spent += order.total_amount
        order.customer.last_visit = timezone.now()
        order.customer.save(update_fields=['total_orders', 'total_spent', 'last_visit'])
        
        return order


class OrderListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for order list views"""
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    customer_phone = serializers.CharField(source='customer.phone', read_only=True)
    total_pieces = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'customer_name', 'customer_phone',
            'status', 'payment_method', 'total_amount', 'total_pieces',
            'expected_completion', 'created_at'
        ]


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    """Serializer for OrderStatusHistory model"""
    changed_by_name = serializers.CharField(source='changed_by.get_full_name', read_only=True)
    
    class Meta:
        model = OrderStatusHistory
        fields = [
            'id', 'old_status', 'new_status', 'changed_by', 'changed_by_name',
            'notes', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']


class OrderUpdateStatusSerializer(serializers.ModelSerializer):
    """Serializer for updating order status"""
    notes = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = Order
        fields = ['status', 'notes']
    
    def update(self, instance, validated_data):
        """Update status and create history entry"""
        old_status = instance.status
        new_status = validated_data.get('status', old_status)
        notes = validated_data.pop('notes', '')
        
        # Update the order
        instance = super().update(instance, validated_data)
        
        # Create status history
        if old_status != new_status:
            OrderStatusHistory.objects.create(
                order=instance,
                old_status=old_status,
                new_status=new_status,
                changed_by=self.context['request'].user,
                notes=notes
            )
            
            # Update completion timestamp if needed
            if new_status == 'completed' and not instance.completed_at:
                instance.completed_at = timezone.now()
                instance.save(update_fields=['completed_at'])
            elif new_status == 'delivered' and not instance.delivered_at:
                instance.delivered_at = timezone.now()
                instance.save(update_fields=['delivered_at'])
        
        return instance


class ReceiptSerializer(serializers.ModelSerializer):
    """Serializer for Receipt model"""
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    generated_by_name = serializers.CharField(source='generated_by.get_full_name', read_only=True)
    
    class Meta:
        model = Receipt
        fields = [
            'id', 'receipt_number', 'order', 'order_number',
            'generated_at', 'generated_by', 'generated_by_name',
            'content', 'email_sent', 'email_sent_at', 'sms_sent', 'sms_sent_at'
        ]
        read_only_fields = [
            'id', 'receipt_number', 'generated_at', 'generated_by_name'
        ]


class OrderDetailSerializer(OrderSerializer):
    """Extended serializer for order details with full related data"""
    customer = CustomerListSerializer(read_only=True)
    lines = OrderLineSerializer(many=True, read_only=True)
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)
    receipt = ReceiptSerializer(read_only=True)
    
    class Meta(OrderSerializer.Meta):
        fields = OrderSerializer.Meta.fields + ['status_history', 'receipt']
