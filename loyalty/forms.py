from django import forms
from .models import LoyaltyRule
import json

class LoyaltyRuleForm(forms.ModelForm):
    """Form for creating and updating Loyalty Rules."""

    class Meta:
        model = LoyaltyRule
        fields = ['name', 'trigger_type', 'config', 'reward', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 5th Order Bonus'}),
            'trigger_type': forms.Select(attrs={'class': 'form-select'}),
            'config': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'e.g., {\"threshold\": 5}'}),
            'reward': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'e.g., {\"type\": \"POINTS\", \"amount\": 100}'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
            'config': 'Enter a valid JSON configuration for the trigger. E.g., {"threshold": 5}',
            'reward': 'Enter a valid JSON configuration for the reward. E.g., {"type": "POINTS", "amount": 100}',
        }

    def clean_config(self):
        """Validate that the config field contains valid JSON."""
        config_data = self.cleaned_data['config']
        try:
            # Attempt to parse the JSON to ensure it's valid
            json.loads(config_data)
        except (json.JSONDecodeError, TypeError) as exc:
            raise forms.ValidationError("Invalid JSON format in Configuration.", code='invalid_json') from exc
        return config_data

    def clean_reward(self):
        """Validate that the reward field contains valid JSON."""
        reward_data = self.cleaned_data['reward']
        try:
            # Attempt to parse the JSON to ensure it's valid
            json.loads(reward_data)
        except (json.JSONDecodeError, TypeError) as exc:
            raise forms.ValidationError("Invalid JSON format in Reward.", code='invalid_json') from exc
        return reward_data
