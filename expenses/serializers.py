from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from django.contrib.auth.models import User
from .models import ExpenseCategory, Expense, ExpenseAttachment, ExpenseApprovalRequest
from decimal import Decimal


class ExpenseCategorySerializer(serializers.ModelSerializer):
    """Serializer for expense categories"""
    monthly_total = serializers.SerializerMethodField()
    budget_usage_percentage = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = ExpenseCategory
        fields = [
            'id', 'name', 'description', 'icon', 'color', 'is_active',
            'monthly_budget', 'monthly_total', 'budget_usage_percentage',
            'created_at', 'updated_at', 'created_by', 'created_by_name'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by']
    
    @extend_schema_field(serializers.DecimalField(max_digits=15, decimal_places=2))
    def get_monthly_total(self, obj):
        """Get current month's total expenses"""
        from django.utils import timezone
        now = timezone.now()
        return obj.get_monthly_total(now.year, now.month)
    
    @extend_schema_field(serializers.DecimalField(max_digits=5, decimal_places=2))
    def get_budget_usage_percentage(self, obj):
        """Get current month's budget usage percentage"""
        from django.utils import timezone
        now = timezone.now()
        return obj.get_budget_usage_percentage(now.year, now.month)


class ExpenseCategoryListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for category lists"""
    expense_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = ExpenseCategory
        fields = ['id', 'name', 'icon', 'color', 'is_active', 'expense_count']


class ExpenseAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for expense attachments"""
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    file_size = serializers.SerializerMethodField()
    
    class Meta:
        model = ExpenseAttachment
        fields = [
            'id', 'file', 'description', 'uploaded_at', 
            'uploaded_by', 'uploaded_by_name', 'file_size'
        ]
        read_only_fields = ['uploaded_at', 'uploaded_by']
    
    @extend_schema_field(serializers.IntegerField())
    def get_file_size(self, obj):
        """Get file size in bytes"""
        try:
            return obj.file.size
        except (ValueError, OSError):
            return 0


class ExpenseSerializer(serializers.ModelSerializer):
    """Serializer for expenses"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    attachments = ExpenseAttachmentSerializer(many=True, read_only=True)
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    
    class Meta:
        model = Expense
        fields = [
            'id', 'category', 'category_name', 'category_icon', 'description',
            'amount', 'expense_date', 'receipt_image', 'notes',
            'is_approved', 'approved_by', 'approved_by_name', 'approved_at',
            'created_at', 'updated_at', 'created_by', 'created_by_name',
            'attachments', 'can_edit', 'can_delete'
        ]
        read_only_fields = [
            'created_at', 'updated_at', 'created_by', 'is_approved',
            'approved_by', 'approved_at'
        ]
    
    @extend_schema_field(serializers.BooleanField())
    def get_can_edit(self, obj):
        """Check if current user can edit this expense"""
        request = self.context.get('request')
        return obj.can_be_edited_by(request.user) if request else False
    
    @extend_schema_field(serializers.BooleanField())
    def get_can_delete(self, obj):
        """Check if current user can delete this expense"""
        request = self.context.get('request')
        return obj.can_be_deleted_by(request.user) if request else False
    
    def validate_amount(self, value):
        """Validate expense amount"""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value


class ExpenseListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for expense lists"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_color = serializers.CharField(source='category.color', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = Expense
        fields = [
            'id', 'category', 'category_name', 'category_color', 'description',
            'amount', 'expense_date', 'is_approved', 
            'created_at', 'created_by_name'
        ]


class ExpenseCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating expenses"""
    
    class Meta:
        model = Expense
        fields = [
            'category', 'description', 'amount', 'expense_date',
            'receipt_image', 'notes'
        ]
    
    def validate_amount(self, value):
        """Validate expense amount"""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value


class ExpenseApprovalRequestSerializer(serializers.ModelSerializer):
    """Serializer for expense approval requests"""
    requested_by_name = serializers.CharField(source='requested_by.get_full_name', read_only=True)
    responded_by_name = serializers.CharField(source='responded_by.get_full_name', read_only=True)
    expense_description = serializers.CharField(source='expense.description', read_only=True)
    expense_amount = serializers.DecimalField(source='expense.amount', max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = ExpenseApprovalRequest
        fields = [
            'id', 'expense', 'expense_description', 'expense_amount',
            'requested_by', 'requested_by_name', 'requested_at', 'message',
            'status', 'responded_by', 'responded_by_name', 'responded_at',
            'response_message'
        ]
        read_only_fields = [
            'requested_at', 'responded_by', 'responded_at'
        ]


class ExpenseStatsSerializer(serializers.Serializer):
    """Serializer for expense statistics"""
    total_expenses = serializers.DecimalField(max_digits=12, decimal_places=2)
    approved_expenses = serializers.DecimalField(max_digits=12, decimal_places=2)
    pending_expenses = serializers.DecimalField(max_digits=12, decimal_places=2)
    expense_count = serializers.IntegerField()
    categories_count = serializers.IntegerField()
    top_categories = serializers.ListField(child=serializers.DictField())
    monthly_trend = serializers.ListField(child=serializers.DictField())
