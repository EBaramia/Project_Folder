from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib import messages
from .forms import AddCommentForm, AddFileForm
from django.views import View
from .models import Lead
from client_app.models import Client, Comment as ClientComment
from team.models import Team
from django.views.generic import CreateView, ListView, DeleteView, DetailView, UpdateView


class LeadListView(ListView):
    model = Lead
    template_name = 'lead/leads_list.html'
    context_object_name = 'leads'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        queryset = super(LeadListView, self).get_queryset()
        return queryset.filter(
            created_by=self.request.user, converted_to_client=False)


class LeadDeleteView(DeleteView):
    model = Lead
    success_url = reverse_lazy('lead:leads_list')

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        queryset = super(LeadDeleteView, self).get_queryset()
        return queryset.filter(
            created_by=self.request.user, pk=self.kwargs.get('pk'))

    def post(self, request, *args, **kwargs):
        lead = self.get_object()
        lead.delete()
        return redirect(self.success_url)


class LeadUpdateView(UpdateView):
    model = Lead
    template_name = 'lead/leads_edit.html'
    fields = ('name', 'email', 'description', 'priority', 'status', )
    success_url = reverse_lazy('lead:leads_list')

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        queryset = super(LeadUpdateView, self).get_queryset()
        return queryset.filter(
            created_by=self.request.user, pk=self.kwargs.get('pk'))


class LeadDetailView(DetailView):
    model = Lead
    template_name = 'lead/leads_detail.html'
    context_object_name = 'lead'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = AddCommentForm()
        context['fileform'] = AddFileForm()

        return context

    def get_queryset(self):
        queryset = super(LeadDetailView, self).get_queryset()
        return queryset.filter(
            created_by=self.request.user, pk=self.kwargs.get('pk'))


class LeadCreateView(CreateView):
    model = Lead
    template_name = 'lead/add_lead.html'
    fields = ('name', 'email', 'description', 'priority', 'status', )
    success_url = reverse_lazy('lead:leads_list')

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        team = Team.objects.filter(created_by=self.request.user)[0]
        context['team'] = team
        context['title'] = 'Add lead'
        return context

    def form_valid(self, form):
        team = Team.objects.filter(created_by=self.request.user)[0]
        self.object = form.save(commit=False)
        self.object.created_by = self.request.user
        self.object.team = team
        self.object.save()
        return redirect(self.get_success_url())


class AddFileView(View):
    def post(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        form = AddFileForm(request.POST, request.FILES)
        if form.is_valid():
            team = Team.objects.filter(created_by=self.request.user)[0]
            file = form.save(commit=False)
            file.team = team
            file.lead_id = pk
            file.created_by = request.user
            file.save()
        return redirect('lead:leads_detail', pk=pk)


class AddCommentView(View):
    def post(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        form = AddCommentForm(request.POST)
        if form.is_valid():
            team = Team.objects.filter(created_by=self.request.user)[0]
            comment = form.save(commit=False)
            comment.team = team
            comment.created_by = request.user
            comment.lead_id = pk
            comment.save()
        return redirect('lead:leads_detail', pk=pk)


class ConvertToClientView(View):
    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        lead = get_object_or_404(Lead, created_by=request.user, pk=pk)
        team = Team.objects.filter(created_by=request.user)[0]

        client = Client.objects.create(
            name=lead.name,
            email=lead.email,
            description=lead.description,
            created_by=request.user,
            team=team,
        )
        lead.converted_to_client = True
        lead.save()

        comments = lead.comments.all()
        for comment in comments:
            ClientComment.objects.create(
                team=team,
                client=client,
                content=comment.content,
                created_by=comment.created_by
            )

        messages.success(request, 'The lead was converted to a client.')

        return redirect('lead:leads_list')
