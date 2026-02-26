from django import forms

from .models import ControleMargem


class ControleMargemForm(forms.ModelForm):
    class Meta:
        model = ControleMargem
        exclude = ("empresa",)
