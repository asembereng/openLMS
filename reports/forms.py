from django import forms

from .models import ReportTemplate

EXPORT_CHOICES = [
    ('', 'None'),
    ('pdf', 'PDF'),
    ('excel', 'Excel'),
    ('csv', 'CSV'),
    ('json', 'JSON'),
]

class ReportGenerationForm(forms.Form):
    """Form for selecting and generating a report"""
    template = forms.ModelChoiceField(
        queryset=ReportTemplate.objects.none(),  # type: ignore
        empty_label="-- Select Template --",
        label="Report Template",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control'}
        )
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control'}
        )
    )
    export_format = forms.ChoiceField(
        choices=EXPORT_CHOICES,
        required=False,
        label="Export Format",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter templates based on user access
        qs = ReportTemplate.objects.filter(is_active=True)  # type: ignore
        accessible = [t.id for t in qs if t.can_be_accessed_by(user)]  # type: ignore
        self.fields['template'].queryset = ReportTemplate.objects.filter(id__in=accessible)  # type: ignore
        self.user = user

        # If template selected in data or initial, add dynamic filter fields
        data = kwargs.get('data') or {}
        tpl_id = data.get('template')
        if tpl_id:
            try:
                tpl = ReportTemplate.objects.get(pk=tpl_id, is_active=True)  # type: ignore
                cfg = tpl.config or {}
                if isinstance(cfg, str):
                    try:
                        import json
                        cfg = json.loads(cfg)
                    except Exception:
                        cfg = {}
                f_list = cfg.get('filters', []) if isinstance(cfg.get('filters'), list) else []
                for f in f_list:
                    if not isinstance(f, dict):
                        continue
                    name = f.get('name')
                    if not name:
                        continue
                    ftype = f.get('type')
                    if ftype == 'date_range':
                        self.fields[f"{name}_from"] = forms.DateField(
                            required=False,
                            label=f.get('label_from', f"{name} From"),
                            widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
                        )
                        self.fields[f"{name}_to"] = forms.DateField(
                            required=False,
                            label=f.get('label_to', f"{name} To"),
                            widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
                        )
                    elif ftype == 'choice':
                        choices = f.get('choices', [])
                        self.fields[name] = forms.ChoiceField(
                            choices=[('', '-- Select --')] + choices,
                            required=False,
                            label=f.get('label', name),
                            widget=forms.Select(attrs={'class': 'form-select'})
                        )
                    elif ftype == 'text':
                        self.fields[name] = forms.CharField(
                            required=False,
                            label=f.get('label', name),
                            widget=forms.TextInput(attrs={'class': 'form-control'})
                        )
            except ReportTemplate.DoesNotExist:
                pass

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('date_from')
        end = cleaned.get('date_to')
        if start and end and start > end:
            raise forms.ValidationError("Start date must be before end date.")
        return cleaned
