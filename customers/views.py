from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator

from rest_framework import generics, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Customer
from .forms import CustomerForm
from .serializers import CustomerSerializer, CustomerCreateSerializer, CustomerListSerializer, CustomerStatsSerializer
from loyalty.models import LoyaltyAccount


# Web Views
class CustomerListView(LoginRequiredMixin, ListView):
    """List view for customers with search and filtering"""
    model = Customer
    template_name = 'customers/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Customer.objects.select_related('created_by')
        search_query = self.request.GET.get('search', '')
        
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(phone__icontains=search_query) |
                Q(email__icontains=search_query)
            )
        
        # Filter by status
        status_filter = self.request.GET.get('status', '')
        if status_filter == 'active':
            queryset = queryset.filter(is_active=True)
        elif status_filter == 'inactive':
            queryset = queryset.filter(is_active=False)
            
        return queryset.order_by('-last_visit', 'name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        return context


class CustomerDetailView(LoginRequiredMixin, DetailView):
    """Detail view for customer with order history"""
    model = Customer
    template_name = 'customers/customer_detail.html'
    context_object_name = 'customer'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get recent orders for this customer
        # context['recent_orders'] = self.object.orders.select_related(
        #     'service', 'created_by'
        # ).order_by('-created_at')[:10]
        
        # Add loyalty points to the context
        try:
            context['loyalty_points'] = self.object.loyaltyaccount.points_balance
        except LoyaltyAccount.DoesNotExist:
            context['loyalty_points'] = 0
            
        return context


class CustomerCreateView(LoginRequiredMixin, CreateView):
    """Create view for new customers"""
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form_modern.html'
    success_url = reverse_lazy('customers:list')
    
    def get_initial(self):
        """Pre-fill name field if provided in URL"""
        initial = super().get_initial()
        name = self.request.GET.get('name', '')
        if name:
            initial['name'] = name
        return initial
    
    def get_success_url(self):
        """Handle return URL for POS integration"""
        next_url = self.request.GET.get('next')
        if next_url:
            # Add the customer ID to the return URL for POS to select the customer
            separator = '&' if '?' in next_url else '?'
            return f"{next_url}{separator}customer_created={self.object.id}"
        return super().get_success_url()
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, f'Customer "{form.instance.name}" created successfully.')
        return super().form_valid(form)


class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    """Update view for existing customers"""
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form_modern.html'
    
    def get_success_url(self):
        return reverse_lazy('customers:detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, f'Customer "{form.instance.name}" updated successfully.')
        return super().form_valid(form)


@login_required
def customer_search_ajax(request):
    """AJAX endpoint for customer search in POS"""
    search_term = request.GET.get('q', '').strip()
    
    if len(search_term) < 2:
        return JsonResponse({'customers': []})
    
    customers = Customer.objects.filter(
        Q(name__icontains=search_term) |
        Q(phone__icontains=search_term),
        is_active=True
    ).values('id', 'name', 'phone', 'email')[:10]
    
    return JsonResponse({'customers': list(customers)})


# API Views
@extend_schema(
    tags=['customers'],
    summary='List and Create Customers',
    description='Retrieve a paginated list of customers or create a new customer profile.',
    parameters=[
        OpenApiParameter(
            name='search',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Search customers by name, phone, or email'
        ),
        OpenApiParameter(
            name='is_active',
            type=OpenApiTypes.BOOL,
            location=OpenApiParameter.QUERY,
            description='Filter by active status'
        ),
        OpenApiParameter(
            name='ordering',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Order by: name, last_visit, total_spent, created_at'
        ),
    ],
    examples=[
        OpenApiExample(
            'List Active Customers',
            summary='Get active customers with search',
            description='Example of fetching active customers with name search',
            value={
                "count": 25,
                "next": "http://127.0.0.1:8000/customers/api/?page=2",
                "previous": None,
                "results": [
                    {
                        "id": 1,
                        "name": "John Doe",
                        "phone": "+234-800-123-4567",
                        "email": "john.doe@email.com",
                        "address": "123 Lagos Street, Lagos",
                        "is_active": True,
                        "total_spent": "150.00",
                        "last_visit": "2025-01-15T10:30:00Z",
                        "created_at": "2024-12-01T08:00:00Z"
                    }
                ]
            },
            request_only=False,
            response_only=True,
        ),
        OpenApiExample(
            'Create Customer',
            summary='Create a new customer',
            description='Example of creating a new customer profile',
            value={
                "name": "Jane Smith",
                "phone": "+234-800-765-4321",
                "email": "jane.smith@email.com",
                "address": "456 Abuja Road, Abuja"
            },
            request_only=True,
            response_only=False,
        ),
    ],
    extensions={
        'x-code-samples': [
            {
                'lang': 'curl',
                'label': 'cURL',
                'source': '''curl -X GET "http://127.0.0.1:8000/customers/api/?search=john&is_active=true" \\
  -H "Accept: application/json" \\
  -H "Authorization: Bearer YOUR_JWT_TOKEN"'''
            },
            {
                'lang': 'python',
                'label': 'Python (requests)',
                'source': '''import requests

url = "http://127.0.0.1:8000/customers/api/"
headers = {
    "Accept": "application/json",
    "Authorization": "Bearer YOUR_JWT_TOKEN"
}
params = {
    "search": "john",
    "is_active": True,
    "page": 1
}

response = requests.get(url, headers=headers, params=params)
customers = response.json()
print(f"Found {customers['count']} customers")'''
            },
            {
                'lang': 'javascript',
                'label': 'JavaScript (fetch)',
                'source': '''const url = "http://127.0.0.1:8000/customers/api/?search=john&is_active=true";

fetch(url, {
  method: 'GET',
  headers: {
    'Accept': 'application/json',
    'Authorization': 'Bearer YOUR_JWT_TOKEN'
  }
})
.then(response => response.json())
.then(data => {
  console.log(`Found ${data.count} customers`);
  console.log(data.results);
});'''
            },
            {
                'lang': 'php',
                'label': 'PHP',
                'source': '''<?php
$url = "http://127.0.0.1:8000/customers/api/?search=john&is_active=true";

$headers = array(
    'Accept: application/json',
    'Authorization: Bearer YOUR_JWT_TOKEN'
);

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

$response = curl_exec($ch);
$data = json_decode($response, true);

echo "Found " . $data['count'] . " customers\\n";
curl_close($ch);
?>'''
            },
            {
                'lang': 'csharp',
                'label': 'C#',
                'source': '''using System.Net.Http;
using System.Threading.Tasks;
using Newtonsoft.Json;

var client = new HttpClient();
client.DefaultRequestHeaders.Add("Authorization", "Bearer YOUR_JWT_TOKEN");

var response = await client.GetAsync(
    "http://127.0.0.1:8000/customers/api/?search=john&is_active=true"
);

if (response.IsSuccessStatusCode)
{
    var content = await response.Content.ReadAsStringAsync();
    dynamic data = JsonConvert.DeserializeObject(content);
    Console.WriteLine($"Found {data.count} customers");
}'''
            },
            {
                'lang': 'go',
                'label': 'Go',
                'source': '''package main

import (
    "fmt"
    "net/http"
    "io/ioutil"
    "encoding/json"
)

type CustomerResponse struct {
    Count int `json:"count"`
    Results []map[string]interface{} `json:"results"`
}

func main() {
    client := &http.Client{}
    req, _ := http.NewRequest("GET", 
        "http://127.0.0.1:8000/customers/api/?search=john&is_active=true", nil)
    
    req.Header.Add("Accept", "application/json")
    req.Header.Add("Authorization", "Bearer YOUR_JWT_TOKEN")
    
    resp, _ := client.Do(req)
    defer resp.Body.Close()
    
    body, _ := ioutil.ReadAll(resp.Body)
    
    var data CustomerResponse
    json.Unmarshal(body, &data)
    
    fmt.Printf("Found %d customers\\n", data.Count)
}'''
            }
        ]
    }
)
class CustomerListCreateAPIView(generics.ListCreateAPIView):
    """API view for listing and creating customers"""
    queryset = Customer.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'phone', 'email']
    ordering_fields = ['name', 'last_visit', 'total_spent', 'created_at']
    ordering = ['-last_visit', 'name']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CustomerCreateSerializer
        return CustomerListSerializer
    
    def get_queryset(self):
        return Customer.objects.select_related('created_by')


@extend_schema(
    tags=['customers'],
    summary='Retrieve and Update Customer',
    description='Get detailed information about a specific customer or update their profile.',
    examples=[
        OpenApiExample(
            'Customer Detail Response',
            summary='Customer details with loyalty information',
            description='Complete customer profile including loyalty points and order history',
            value={
                "id": 1,
                "name": "John Doe",
                "phone": "+234-800-123-4567",
                "email": "john.doe@email.com",
                "address": "123 Lagos Street, Lagos",
                "is_active": True,
                "total_spent": "150.00",
                "last_visit": "2025-01-15T10:30:00Z",
                "created_at": "2024-12-01T08:00:00Z",
                "loyalty_points": 75,
                "total_orders": 12
            },
            request_only=False,
            response_only=True,
        ),
    ],
    extensions={
        'x-code-samples': [
            {
                'lang': 'curl',
                'label': 'cURL',
                'source': '''curl -X GET "http://127.0.0.1:8000/customers/api/1/" \\
  -H "Accept: application/json" \\
  -H "Authorization: Bearer YOUR_JWT_TOKEN"'''
            },
            {
                'lang': 'python',
                'label': 'Python (requests)',
                'source': '''import requests

url = "http://127.0.0.1:8000/customers/api/1/"
headers = {
    "Accept": "application/json",
    "Authorization": "Bearer YOUR_JWT_TOKEN"
}

response = requests.get(url, headers=headers)
customer = response.json()
print(f"Customer: {customer['name']}")
print(f"Loyalty Points: {customer.get('loyalty_points', 0)}")'''
            },
            {
                'lang': 'javascript',
                'label': 'JavaScript (fetch)',
                'source': '''const customerId = 1;
const url = `http://127.0.0.1:8000/customers/api/${customerId}/`;

fetch(url, {
  method: 'GET',
  headers: {
    'Accept': 'application/json',
    'Authorization': 'Bearer YOUR_JWT_TOKEN'
  }
})
.then(response => response.json())
.then(customer => {
  console.log(`Customer: ${customer.name}`);
  console.log(`Total Spent: ${customer.total_spent}`);
});'''
            },
            {
                'lang': 'php',
                'label': 'PHP',
                'source': '''<?php
$customerId = 1;
$url = "http://127.0.0.1:8000/customers/api/{$customerId}/";

$headers = array(
    'Accept: application/json',
    'Authorization: Bearer YOUR_JWT_TOKEN'
);

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

$response = curl_exec($ch);
$customer = json_decode($response, true);

echo "Customer: " . $customer['name'] . "\\n";
echo "Total Spent: " . $customer['total_spent'] . "\\n";
curl_close($ch);
?>'''
            },
            {
                'lang': 'csharp',
                'label': 'C#',
                'source': '''using System.Net.Http;
using System.Threading.Tasks;
using Newtonsoft.Json;

var customerId = 1;
var client = new HttpClient();
client.DefaultRequestHeaders.Add("Authorization", "Bearer YOUR_JWT_TOKEN");

var response = await client.GetAsync(
    $"http://127.0.0.1:8000/customers/api/{customerId}/"
);

if (response.IsSuccessStatusCode)
{
    var content = await response.Content.ReadAsStringAsync();
    dynamic customer = JsonConvert.DeserializeObject(content);
    Console.WriteLine($"Customer: {customer.name}");
    Console.WriteLine($"Total Spent: {customer.total_spent}");
}'''
            },
            {
                'lang': 'go',
                'label': 'Go',
                'source': '''package main

import (
    "fmt"
    "net/http"
    "io/ioutil"
    "encoding/json"
)

type Customer struct {
    ID          int    `json:"id"`
    Name        string `json:"name"`
    Phone       string `json:"phone"`
    Email       string `json:"email"`
    TotalSpent  string `json:"total_spent"`
}

func main() {
    customerId := 1
    client := &http.Client{}
    url := fmt.Sprintf("http://127.0.0.1:8000/customers/api/%d/", customerId)
    
    req, _ := http.NewRequest("GET", url, nil)
    req.Header.Add("Accept", "application/json")
    req.Header.Add("Authorization", "Bearer YOUR_JWT_TOKEN")
    
    resp, _ := client.Do(req)
    defer resp.Body.Close()
    
    body, _ := ioutil.ReadAll(resp.Body)
    
    var customer Customer
    json.Unmarshal(body, &customer)
    
    fmt.Printf("Customer: %s\\n", customer.Name)
    fmt.Printf("Total Spent: %s\\n", customer.TotalSpent)
}'''
            }
        ]
    }
)
class CustomerRetrieveUpdateAPIView(generics.RetrieveUpdateAPIView):
    """API view for retrieving and updating individual customers"""
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Customer.objects.select_related('created_by')


@extend_schema(
    tags=['customers'],
    summary='Customer Statistics',
    description='Get comprehensive customer analytics and statistics.',
    responses=CustomerStatsSerializer,
    examples=[
        OpenApiExample(
            'Customer Statistics Response',
            summary='Business analytics for customer management',
            description='Key metrics for customer base analysis',
            value={
                "total_customers": 150,
                "active_customers": 142,
                "inactive_customers": 8,
                "new_customers_this_month": 12
            },
            request_only=False,
            response_only=True,
        ),
    ],
    extensions={
        'x-code-samples': [
            {
                'lang': 'curl',
                'label': 'cURL',
                'source': '''curl -X GET "http://127.0.0.1:8000/customers/api/stats/" \\
  -H "Accept: application/json" \\
  -H "Authorization: Bearer YOUR_JWT_TOKEN"'''
            },
            {
                'lang': 'python',
                'label': 'Python (requests)',
                'source': '''import requests

url = "http://127.0.0.1:8000/customers/api/stats/"
headers = {
    "Accept": "application/json",
    "Authorization": "Bearer YOUR_JWT_TOKEN"
}

response = requests.get(url, headers=headers)
stats = response.json()

print(f"Total Customers: {stats['total_customers']}")
print(f"Active Customers: {stats['active_customers']}")
print(f"New This Month: {stats['new_customers_this_month']}")'''
            },
            {
                'lang': 'javascript',
                'label': 'JavaScript (fetch)',
                'source': '''fetch('http://127.0.0.1:8000/customers/api/stats/', {
  method: 'GET',
  headers: {
    'Accept': 'application/json',
    'Authorization': 'Bearer YOUR_JWT_TOKEN'
  }
})
.then(response => response.json())
.then(stats => {
  console.log('Customer Statistics:');
  console.log(`Total: ${stats.total_customers}`);
  console.log(`Active: ${stats.active_customers}`);
  console.log(`New this month: ${stats.new_customers_this_month}`);
});'''
            },
            {
                'lang': 'php',
                'label': 'PHP',
                'source': '''<?php
$url = "http://127.0.0.1:8000/customers/api/stats/";

$headers = array(
    'Accept: application/json',
    'Authorization: Bearer YOUR_JWT_TOKEN'
);

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

$response = curl_exec($ch);
$stats = json_decode($response, true);

echo "Customer Statistics:\\n";
echo "Total: " . $stats['total_customers'] . "\\n";
echo "Active: " . $stats['active_customers'] . "\\n";
echo "New this month: " . $stats['new_customers_this_month'] . "\\n";

curl_close($ch);
?>'''
            },
            {
                'lang': 'csharp',
                'label': 'C#',
                'source': '''using System.Net.Http;
using System.Threading.Tasks;
using Newtonsoft.Json;

public class CustomerStats
{
    public int TotalCustomers { get; set; }
    public int ActiveCustomers { get; set; }
    public int InactiveCustomers { get; set; }
    public int NewCustomersThisMonth { get; set; }
}

var client = new HttpClient();
client.DefaultRequestHeaders.Add("Authorization", "Bearer YOUR_JWT_TOKEN");

var response = await client.GetAsync("http://127.0.0.1:8000/customers/api/stats/");

if (response.IsSuccessStatusCode)
{
    var content = await response.Content.ReadAsStringAsync();
    var stats = JsonConvert.DeserializeObject<CustomerStats>(content);
    
    Console.WriteLine($"Total Customers: {stats.TotalCustomers}");
    Console.WriteLine($"Active Customers: {stats.ActiveCustomers}");
    Console.WriteLine($"New This Month: {stats.NewCustomersThisMonth}");
}'''
            },
            {
                'lang': 'go',
                'label': 'Go',
                'source': '''package main

import (
    "fmt"
    "net/http"
    "io/ioutil"
    "encoding/json"
)

type CustomerStats struct {
    TotalCustomers         int `json:"total_customers"`
    ActiveCustomers        int `json:"active_customers"`
    InactiveCustomers      int `json:"inactive_customers"`
    NewCustomersThisMonth  int `json:"new_customers_this_month"`
}

func main() {
    client := &http.Client{}
    req, _ := http.NewRequest("GET", 
        "http://127.0.0.1:8000/customers/api/stats/", nil)
    
    req.Header.Add("Accept", "application/json")
    req.Header.Add("Authorization", "Bearer YOUR_JWT_TOKEN")
    
    resp, _ := client.Do(req)
    defer resp.Body.Close()
    
    body, _ := ioutil.ReadAll(resp.Body)
    
    var stats CustomerStats
    json.Unmarshal(body, &stats)
    
    fmt.Printf("Customer Statistics:\\n")
    fmt.Printf("Total: %d\\n", stats.TotalCustomers)
    fmt.Printf("Active: %d\\n", stats.ActiveCustomers)
    fmt.Printf("New this month: %d\\n", stats.NewCustomersThisMonth)
}'''
            }
        ]
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def customer_stats_api(request):
    """API endpoint for customer statistics"""
    total_customers = Customer.objects.count()
    active_customers = Customer.objects.filter(is_active=True).count()
    new_customers_this_month = Customer.objects.filter(
        created_at__month=timezone.now().month,
        created_at__year=timezone.now().year
    ).count()
    
    return Response({
        'total_customers': total_customers,
        'active_customers': active_customers,
        'inactive_customers': total_customers - active_customers,
        'new_customers_this_month': new_customers_this_month
    })
