from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from loyalty.models import LoyaltyAccount, LoyaltyTransaction, LoyaltyRule, Referral
from .forms import LoyaltyRuleForm
from . import rule_templates

class AdminRequiredMixin(UserPassesTestMixin):
    """Ensures the user is a superuser or belongs to the 'Admin' group."""
    def test_func(self):
        return self.request.user.is_superuser or \
               self.request.user.groups.filter(name='Admin').exists()

class LoyaltyRuleTemplateSelectionView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """Displays available loyalty rule templates for creation."""
    template_name = 'loyalty/rule_template_selection.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['templates'] = rule_templates.get_loyalty_templates()
        return context

class LoyaltyAccountListView(LoginRequiredMixin, ListView):
    model = LoyaltyAccount
    template_name = 'loyalty/loyalty_account_list.html'
    context_object_name = 'accounts'

class LoyaltyTransactionListView(ListView):
    model = LoyaltyTransaction
    template_name = 'loyalty/loyalty_transaction_list.html'
    context_object_name = 'transactions'

class LoyaltyRuleListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """View to list and manage Loyalty Rules. (Admin only)"""
    model = LoyaltyRule
    template_name = 'loyalty/rule_list.html'
    context_object_name = 'rules'
    paginate_by = 10

class LoyaltyRuleCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """View to create a new Loyalty Rule. (Admin only)"""
    model = LoyaltyRule
    form_class = LoyaltyRuleForm
    template_name = 'loyalty/rule_form.html'
    success_url = reverse_lazy('loyalty:rule_list')

    def get_initial(self):
        """Pre-populates the form if a template is selected."""
        initial = super().get_initial()
        template_id = self.request.GET.get('template')
        if template_id:
            templates = rule_templates.get_loyalty_templates()
            selected_template = next((t for t in templates if t['id'] == template_id), None)
            if selected_template:
                initial['name'] = selected_template['name']
                initial['trigger_type'] = selected_template['trigger_type']
                initial['config'] = selected_template['config']
                initial['reward'] = selected_template['reward']
        return initial

class LoyaltyRuleUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    """View to update an existing Loyalty Rule. (Admin only)"""
    model = LoyaltyRule
    form_class = LoyaltyRuleForm
    template_name = 'loyalty/rule_form.html'
    success_url = reverse_lazy('loyalty:rule_list')

class LoyaltyRuleDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    """View to delete a Loyalty Rule. (Admin only)"""
    model = LoyaltyRule
    template_name = 'loyalty/rule_confirm_delete.html'
    success_url = reverse_lazy('loyalty:rule_list')

class ReferralListView(ListView):
    model = Referral
    template_name = 'loyalty/referral_list.html'
    context_object_name = 'referrals'
