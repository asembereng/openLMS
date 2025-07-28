from rest_framework import serializers
from .models import Customer


class CustomerSerializer(serializers.ModelSerializer):
    """Serializer for Customer model"""
    
    class Meta:
        model = Customer
        fields = [
            'id', 'name', 'phone', 'email', 'address', 'notes',
            'total_orders', 'total_spent', 'last_visit', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'total_orders', 'total_spent', 'last_visit',
            'created_at', 'updated_at'
        ]
    
    def validate_phone(self, value):
        """Validate phone number uniqueness"""
        if self.instance and self.instance.phone == value:
            return value
        
        if Customer.objects.filter(phone=value).exists():
            raise serializers.ValidationError("A customer with this phone number already exists.")
        return value


class CustomerCreateSerializer(CustomerSerializer):
    """Serializer for creating customers"""
    
    def create(self, validated_data):
        """Create customer with current user as creator"""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class CustomerListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for customer list views"""
    
    class Meta:
        model = Customer
        fields = [
            'id', 'name', 'phone', 'email', 'total_orders', 
            'total_spent', 'last_visit', 'is_active'
        ]


class CustomerStatsSerializer(serializers.Serializer):
    """Serializer for customer statistics response"""
    total_customers = serializers.IntegerField()
    active_customers = serializers.IntegerField()
    inactive_customers = serializers.IntegerField()
    new_customers_this_month = serializers.IntegerField()
