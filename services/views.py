from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q, Count
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied

from rest_framework import generics, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import ServiceCategory, Service, ServicePriceHistory
from .serializers import (
    ServiceCategorySerializer, ServiceSerializer, ServiceCreateSerializer,
    ServiceListSerializer, ServicePriceHistorySerializer, ServiceWithCategorySerializer,
    ServiceStatsSerializer, ServicesByCategorySerializer
)
from laundry_management.constraint_handlers import (
    handle_database_constraints, 
    check_delete_constraints,
    get_related_objects_summary
)


class AdminRequiredMixin(UserPassesTestMixin):
    """Mixin to require admin access for certain views"""
    
    def test_func(self):
        return self.request.user.is_superuser or self.request.user.groups.filter(name='Admin').exists()
    
    def handle_no_permission(self):
        raise PermissionDenied("Admin access required")


# Web Views - Service Categories
class ServiceCategoryListView(LoginRequiredMixin, ListView):
    """List view for service categories"""
    model = ServiceCategory
    template_name = 'services/category_list.html'
    context_object_name = 'categories'
    
    def get_queryset(self):
        return ServiceCategory.objects.annotate(
            services_count=Count('services', filter=Q(services__is_active=True))
        ).order_by('display_order', 'name')


class ServiceCategoryCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """Create view for service categories"""
    model = ServiceCategory
    template_name = 'services/category_form.html'
    fields = ['name', 'description', 'icon', 'display_order', 'is_active']
    success_url = reverse_lazy('services:category_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Category "{form.instance.name}" created successfully.')
        return super().form_valid(form)


class ServiceCategoryUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    """Update view for service categories"""
    model = ServiceCategory
    template_name = 'services/category_form.html'
    fields = ['name', 'description', 'icon', 'display_order', 'is_active']
    success_url = reverse_lazy('services:category_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Category "{form.instance.name}" updated successfully.')
        return super().form_valid(form)


# Web Views - Services
class ServiceListView(LoginRequiredMixin, ListView):
    """List view for services with filtering"""
    model = Service
    template_name = 'services/service_list.html'
    context_object_name = 'services'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Service.objects.select_related('category', 'created_by')
        
        # Filter by category
        category_id = self.request.GET.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Search
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(category__name__icontains=search_query)
            )
        
        # Filter by status
        status_filter = self.request.GET.get('status', '')
        if status_filter == 'active':
            queryset = queryset.filter(is_active=True)
        elif status_filter == 'inactive':
            queryset = queryset.filter(is_active=False)
            
        return queryset.order_by('category__display_order', 'display_order', 'name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = ServiceCategory.objects.filter(is_active=True)
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_category'] = self.request.GET.get('category', '')
        context['status_filter'] = self.request.GET.get('status', '')
        return context


class ServiceDetailView(LoginRequiredMixin, DetailView):
    """Detail view for service with price history"""
    model = Service
    template_name = 'services/service_detail.html'
    context_object_name = 'service'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['price_history'] = self.object.price_history.select_related(
            'created_by'
        ).order_by('-effective_date')[:10]
        return context


class ServiceCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """Create view for services"""
    model = Service
    template_name = 'services/service_form_modern.html'
    fields = ['category', 'name', 'description', 'price_per_dozen', 'display_order', 'is_active']
    success_url = reverse_lazy('services:list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, f'Service "{form.instance.name}" created successfully.')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = ServiceCategory.objects.filter(is_active=True)
        return context


class ServiceUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    """Update view for services"""
    model = Service
    template_name = 'services/service_form_modern.html'
    fields = ['category', 'name', 'description', 'price_per_dozen', 'display_order', 'is_active']
    
    def get_success_url(self):
        return self.object.get_absolute_url()
    
    def form_valid(self, form):
        # Track price changes
        if 'price_per_dozen' in form.changed_data:
            # End current price history
            ServicePriceHistory.objects.filter(
                service=form.instance,
                end_date__isnull=True
            ).update(end_date=timezone.now())
            
            # Create new price history entry
            ServicePriceHistory.objects.create(
                service=form.instance,
                price_per_dozen=form.cleaned_data['price_per_dozen'],
                created_by=self.request.user,
                change_reason=f"Price updated from admin panel"
            )
        
        messages.success(self.request, f'Service "{form.instance.name}" updated successfully.')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = ServiceCategory.objects.filter(is_active=True)
        return context


class ServiceDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    """Delete view for services - Admin only with constraint checking"""
    model = Service
    template_name = 'services/service_confirm_delete.html'
    success_url = reverse_lazy('services:list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = self.get_object()
        
        # Check for related objects before showing delete confirmation
        can_delete, error_message, related_objects = check_delete_constraints(
            service, "service"
        )
        
        context['can_delete'] = can_delete
        context['constraint_message'] = error_message
        context['related_objects'] = related_objects
        context['related_summary'] = get_related_objects_summary(service)
        
        return context
    
    @handle_database_constraints
    def delete(self, request, *args, **kwargs):
        service = self.get_object()
        
        # Double-check constraints before deletion
        can_delete, error_message, related_objects = check_delete_constraints(
            service, "service"
        )
        
        if not can_delete:
            messages.error(request, error_message)
            return redirect(self.success_url)
        
        messages.success(request, f'Service "{service.name}" deleted successfully.')
        return super().delete(request, *args, **kwargs)


@login_required
def service_search_ajax(request):
    """AJAX endpoint for service search in POS"""
    search_term = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '')
    
    if len(search_term) < 2 and not category_id:
        return JsonResponse({'services': []})
    
    queryset = Service.objects.filter(is_active=True).select_related('category')
    
    if search_term:
        queryset = queryset.filter(
            Q(name__icontains=search_term) |
            Q(category__name__icontains=search_term)
        )
    
    if category_id:
        queryset = queryset.filter(category_id=category_id)
    
    services = queryset.values(
        'id', 'name', 'price_per_dozen', 
        'category__name'
    )[:20]
    
    # Add unit price calculation
    services_list = []
    for service in services:
        service['unit_price'] = float(service['price_per_dozen']) / 12
        services_list.append(service)
    
    return JsonResponse({'services': services_list})


# API Views - Service Categories
class ServiceCategoryListCreateAPIView(generics.ListCreateAPIView):
    """API view for listing and creating service categories"""
    queryset = ServiceCategory.objects.all()
    serializer_class = ServiceCategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'display_order', 'created_at']
    ordering = ['display_order', 'name']


class ServiceCategoryRetrieveUpdateAPIView(generics.RetrieveUpdateAPIView):
    """API view for retrieving and updating service categories"""
    queryset = ServiceCategory.objects.all()
    serializer_class = ServiceCategorySerializer
    permission_classes = [IsAuthenticated]


# API Views - Services
@extend_schema(
    tags=['services'],
    summary='List and Create Services',
    description='Retrieve available laundry services with pricing or create new service types.',
    parameters=[
        OpenApiParameter(
            name='category',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Filter by service category ID'
        ),
        OpenApiParameter(
            name='is_active',
            type=OpenApiTypes.BOOL,
            location=OpenApiParameter.QUERY,
            description='Filter by active status'
        ),
        OpenApiParameter(
            name='search',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Search services by name, description, or category'
        ),
    ],
    examples=[
        OpenApiExample(
            'Services List Response',
            summary='Available laundry services with pricing',
            description='Complete service catalog with categories and pricing information',
            value={
                "count": 15,
                "results": [
                    {
                        "id": 1,
                        "name": "Dry Cleaning",
                        "description": "Professional dry cleaning service for delicate fabrics",
                        "category": {
                            "id": 1,
                            "name": "Cleaning Services",
                            "description": "Basic cleaning operations"
                        },
                        "price_per_dozen": "120.00",
                        "unit_price": "10.00",
                        "is_active": True,
                        "estimated_duration_hours": 24,
                        "special_instructions": "Handle with care",
                        "created_at": "2024-12-01T08:00:00Z"
                    },
                    {
                        "id": 2,
                        "name": "Wash & Iron",
                        "description": "Standard washing and ironing service",
                        "category": {
                            "id": 1,
                            "name": "Cleaning Services"
                        },
                        "price_per_dozen": "60.00",
                        "unit_price": "5.00",
                        "is_active": True,
                        "estimated_duration_hours": 12
                    }
                ]
            },
            response_only=True,
        ),
        OpenApiExample(
            'Create Service Request',
            summary='Create new service type',
            description='Add a new laundry service with pricing and category',
            value={
                "name": "Premium Starch",
                "description": "Heavy starch treatment for formal wear",
                "category": 2,
                "price_per_dozen": "180.00",
                "estimated_duration_hours": 48,
                "special_instructions": "Use premium starch only",
                "is_active": True
            },
            request_only=True,
        ),
    ],
    extensions={
        'x-code-samples': [
            {
                'lang': 'curl',
                'label': 'cURL - List Services',
                'source': '''curl -X GET "http://127.0.0.1:8000/services/api/?category=1&is_active=true" \\
  -H "Accept: application/json"'''
            },
            {
                'lang': 'curl',
                'label': 'cURL - Create Service',
                'source': '''curl -X POST "http://127.0.0.1:8000/services/api/" \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \\
  -d '{
    "name": "Premium Starch",
    "description": "Heavy starch treatment for formal wear",
    "category": 2,
    "price_per_dozen": "180.00",
    "estimated_duration_hours": 48
  }'
'''
            },
            {
                'lang': 'python',
                'label': 'Python (requests)',
                'source': '''import requests

# List services
url = "http://127.0.0.1:8000/services/api/"
params = {
    "category": 1,
    "is_active": True
}

response = requests.get(url, params=params)
services = response.json()

print(f"Found {services['count']} services")
for service in services['results']:
    unit_price = float(service['price_per_dozen']) / 12
    print(f"{service['name']}: ${unit_price:.2f} per piece")

# Create new service
new_service = {
    "name": "Premium Starch",
    "description": "Heavy starch treatment for formal wear",
    "category": 2,
    "price_per_dozen": "180.00",
    "estimated_duration_hours": 48
}

headers = {"Authorization": "Bearer YOUR_JWT_TOKEN"}
create_response = requests.post(url, json=new_service, headers=headers)

if create_response.status_code == 201:
    print("Service created successfully")'''
            },
            {
                'lang': 'javascript',
                'label': 'JavaScript (fetch)',
                'source': '''// List services by category
fetch('http://127.0.0.1:8000/services/api/?category=1&is_active=true')
  .then(response => response.json())
  .then(data => {
    console.log(`Found ${data.count} services`);
    
    data.results.forEach(service => {
      const unitPrice = parseFloat(service.price_per_dozen) / 12;
      console.log(`${service.name}: $${unitPrice.toFixed(2)} per piece`);
      console.log(`  Category: ${service.category.name}`);
      console.log(`  Duration: ${service.estimated_duration_hours} hours`);
    });
  });

// Create new service
const newService = {
  name: "Premium Starch",
  description: "Heavy starch treatment for formal wear",
  category: 2,
  price_per_dozen: "180.00",
  estimated_duration_hours: 48,
  is_active: true
};

fetch('http://127.0.0.1:8000/services/api/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer YOUR_JWT_TOKEN'
  },
  body: JSON.stringify(newService)
})
.then(response => response.json())
.then(service => {
  console.log(`Created service: ${service.name}`);
  console.log(`Service ID: ${service.id}`);
});'''
            },
            {
                'lang': 'php',
                'label': 'PHP',
                'source': '''<?php
// List services
$url = "http://127.0.0.1:8000/services/api/?category=1&is_active=true";

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_HTTPHEADER, array('Accept: application/json'));

$response = curl_exec($ch);
$services = json_decode($response, true);

echo "Found " . $services['count'] . " services\\n";

foreach ($services['results'] as $service) {
    $unitPrice = floatval($service['price_per_dozen']) / 12;
    echo $service['name'] . ": $" . number_format($unitPrice, 2) . " per piece\\n";
    echo "  Category: " . $service['category']['name'] . "\\n";
    echo "  Duration: " . $service['estimated_duration_hours'] . " hours\\n\\n";
}

// Create new service
$newService = array(
    'name' => 'Premium Starch',
    'description' => 'Heavy starch treatment for formal wear',
    'category' => 2,
    'price_per_dozen' => '180.00',
    'estimated_duration_hours' => 48,
    'is_active' => true
);

curl_setopt($ch, CURLOPT_URL, "http://127.0.0.1:8000/services/api/");
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($newService));
curl_setopt($ch, CURLOPT_HTTPHEADER, array(
    'Content-Type: application/json',
    'Authorization: Bearer YOUR_JWT_TOKEN'
));

$createResponse = curl_exec($ch);
$createdService = json_decode($createResponse, true);

echo "Created service: " . $createdService['name'] . "\\n";
curl_close($ch);
?>'''
            },
            {
                'lang': 'csharp',
                'label': 'C#',
                'source': '''using System.Net.Http;
using System.Text;
using System.Text.Json;

public class ServiceCategory
{
    public int Id { get; set; }
    public string Name { get; set; }
    public string Description { get; set; }
}

public class LaundryService
{
    public int Id { get; set; }
    public string Name { get; set; }
    public string Description { get; set; }
    public ServiceCategory Category { get; set; }
    public decimal PricePerDozen { get; set; }
    public decimal UnitPrice { get; set; }
    public bool IsActive { get; set; }
    public int EstimatedDurationHours { get; set; }
}

public class CreateServiceRequest
{
    public string Name { get; set; }
    public string Description { get; set; }
    public int Category { get; set; }
    public decimal PricePerDozen { get; set; }
    public int EstimatedDurationHours { get; set; }
    public bool IsActive { get; set; } = true;
}

var client = new HttpClient();

// List services
var response = await client.GetAsync(
    "http://127.0.0.1:8000/services/api/?category=1&is_active=true"
);

if (response.IsSuccessStatusCode)
{
    var content = await response.Content.ReadAsStringAsync();
    var servicesData = JsonSerializer.Deserialize<dynamic>(content);
    Console.WriteLine("Services retrieved successfully");
}

// Create new service
var newService = new CreateServiceRequest
{
    Name = "Premium Starch",
    Description = "Heavy starch treatment for formal wear",
    Category = 2,
    PricePerDozen = 180.00m,
    EstimatedDurationHours = 48
};

client.DefaultRequestHeaders.Add("Authorization", "Bearer YOUR_JWT_TOKEN");

var json = JsonSerializer.Serialize(newService);
var createContent = new StringContent(json, Encoding.UTF8, "application/json");

var createResponse = await client.PostAsync(
    "http://127.0.0.1:8000/services/api/", createContent
);

if (createResponse.IsSuccessStatusCode)
{
    Console.WriteLine("Service created successfully");
}'''
            },
            {
                'lang': 'go',
                'label': 'Go',
                'source': '''package main

import (
    "bytes"
    "encoding/json"
    "fmt"
    "net/http"
    "io/ioutil"
)

type ServiceCategory struct {
    ID          int    `json:"id"`
    Name        string `json:"name"`
    Description string `json:"description"`
}

type LaundryService struct {
    ID                      int             `json:"id"`
    Name                    string          `json:"name"`
    Description             string          `json:"description"`
    Category                ServiceCategory `json:"category"`
    PricePerDozen          string          `json:"price_per_dozen"`
    UnitPrice              string          `json:"unit_price"`
    IsActive               bool            `json:"is_active"`
    EstimatedDurationHours int             `json:"estimated_duration_hours"`
}

type CreateServiceRequest struct {
    Name                    string `json:"name"`
    Description             string `json:"description"`
    Category                int    `json:"category"`
    PricePerDozen          string `json:"price_per_dozen"`
    EstimatedDurationHours  int    `json:"estimated_duration_hours"`
    IsActive               bool   `json:"is_active"`
}

type ServicesResponse struct {
    Count   int              `json:"count"`
    Results []LaundryService `json:"results"`
}

func main() {
    client := &http.Client{}
    
    // List services
    req, _ := http.NewRequest("GET", 
        "http://127.0.0.1:8000/services/api/?category=1&is_active=true", nil)
    req.Header.Add("Accept", "application/json")
    
    resp, _ := client.Do(req)
    body, _ := ioutil.ReadAll(resp.Body)
    resp.Body.Close()
    
    var services ServicesResponse
    json.Unmarshal(body, &services)
    
    fmt.Printf("Found %d services\\n", services.Count)
    for _, service := range services.Results {
        fmt.Printf("%s: %s per dozen\\n", service.Name, service.PricePerDozen)
        fmt.Printf("  Category: %s\\n", service.Category.Name)
        fmt.Printf("  Duration: %d hours\\n\\n", service.EstimatedDurationHours)
    }
    
    // Create new service
    newService := CreateServiceRequest{
        Name:                   "Premium Starch",
        Description:            "Heavy starch treatment for formal wear",
        Category:               2,
        PricePerDozen:         "180.00",
        EstimatedDurationHours: 48,
        IsActive:              true,
    }
    
    jsonData, _ := json.Marshal(newService)
    
    createReq, _ := http.NewRequest("POST", 
        "http://127.0.0.1:8000/services/api/", bytes.NewBuffer(jsonData))
    createReq.Header.Set("Content-Type", "application/json")
    createReq.Header.Set("Authorization", "Bearer YOUR_JWT_TOKEN")
    
    createResp, _ := client.Do(createReq)
    defer createResp.Body.Close()
    
    if createResp.StatusCode == 201 {
        fmt.Println("Service created successfully")
    }
}'''
            }
        ]
    }
)
class ServiceListCreateAPIView(generics.ListCreateAPIView):
    """API view for listing and creating services"""
    queryset = Service.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'is_active']
    search_fields = ['name', 'description', 'category__name']
    ordering_fields = ['name', 'price_per_dozen', 'created_at']
    ordering = ['category__display_order', 'display_order', 'name']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ServiceCreateSerializer
        return ServiceListSerializer
    
    def get_queryset(self):
        return Service.objects.select_related('category', 'created_by')


class ServiceRetrieveUpdateAPIView(generics.RetrieveUpdateAPIView):
    """API view for retrieving and updating services"""
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Service.objects.select_related('category', 'created_by')


@extend_schema(responses=ServicesByCategorySerializer(many=True))
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def services_by_category_api(request):
    """API endpoint for services grouped by category"""
    categories = ServiceCategory.objects.filter(is_active=True).prefetch_related(
        'services'
    ).order_by('display_order', 'name')
    
    result = []
    for category in categories:
        active_services = category.services.filter(is_active=True)
        if active_services.exists():
            result.append({
                'id': category.id,
                'name': category.name,
                'icon': category.icon,
                'services': ServiceListSerializer(active_services, many=True).data
            })
    
    return Response(result)


@extend_schema(responses=ServiceStatsSerializer)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def service_stats_api(request):
    """API endpoint for service statistics"""
    total_services = Service.objects.count()
    active_services = Service.objects.filter(is_active=True).count()
    total_categories = ServiceCategory.objects.count()
    active_categories = ServiceCategory.objects.filter(is_active=True).count()
    
    return Response({
        'total_services': total_services,
        'active_services': active_services,
        'inactive_services': total_services - active_services,
        'total_categories': total_categories,
        'active_categories': active_categories
    })
