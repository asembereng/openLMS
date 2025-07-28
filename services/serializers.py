from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import ServiceCategory, Service, ServicePriceHistory


class ServiceCategorySerializer(serializers.ModelSerializer):
    """Serializer for ServiceCategory model"""
    services_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceCategory
        fields = [
            'id', 'name', 'description', 'icon', 'display_order', 
            'is_active', 'services_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'services_count', 'created_at', 'updated_at']
    
    @extend_schema_field(serializers.IntegerField())
    def get_services_count(self, obj):
        return obj.services.filter(is_active=True).count()


class ServiceSerializer(serializers.ModelSerializer):
    """Serializer for Service model"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Service
        fields = [
            'id', 'category', 'category_name', 'name', 'description',
            'price_per_dozen', 'unit_price', 'is_active', 'display_order',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'unit_price', 'created_at', 'updated_at']
    
    def validate_price_per_dozen(self, value):
        """Validate price per dozen is positive"""
        if value <= 0:
            raise serializers.ValidationError("Price per dozen must be greater than 0")
        return value


class ServiceCreateSerializer(ServiceSerializer):
    """Serializer for creating services"""
    
    def create(self, validated_data):
        """Create service with current user as creator"""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class ServiceListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for service list views"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Service
        fields = [
            'id', 'category', 'category_name', 'name', 
            'price_per_dozen', 'unit_price', 'is_active'
        ]


class ServicePriceHistorySerializer(serializers.ModelSerializer):
    """Serializer for ServicePriceHistory model"""
    service_name = serializers.CharField(source='service.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = ServicePriceHistory
        fields = [
            'id', 'service', 'service_name', 'price_per_dozen', 'unit_price',
            'effective_date', 'end_date', 'change_reason', 
            'created_at', 'created_by_name'
        ]
        read_only_fields = [
            'id', 'service_name', 'unit_price', 'created_at', 'created_by_name'
        ]


class ServiceWithCategorySerializer(serializers.ModelSerializer):
    """Service serializer with nested category details"""
    category = ServiceCategorySerializer(read_only=True)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Service
        fields = [
            'id', 'category', 'name', 'description',
            'price_per_dozen', 'unit_price', 'is_active', 'display_order'
        ]


class ServiceStatsSerializer(serializers.Serializer):
    """Serializer for service statistics response"""
    total_services = serializers.IntegerField()
    active_services = serializers.IntegerField()
    inactive_services = serializers.IntegerField()
    total_categories = serializers.IntegerField()
    active_categories = serializers.IntegerField()


class ServicesByCategorySerializer(serializers.Serializer):
    """Serializer for services grouped by category response"""
    id = serializers.IntegerField()
    name = serializers.CharField()
    icon = serializers.CharField()
    services = ServiceListSerializer(many=True)
