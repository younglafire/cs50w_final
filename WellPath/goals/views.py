from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.template.loader import render_to_string
from taxonomy.models import Category, Unit

from .models import Goal, Progress, ProgressPhoto
from .forms import CustomUserCreationForm, GoalForm, GoalEditForm

# Import services
from . import services


# Context processor
def categories_context(request):
    return {'categories': Category.objects.all()}


# =============================================================================
# PUBLIC VIEWS
# =============================================================================

def index(request):
    return render(request, "goals/index.html")


def feed(request):
    """Public feed showing active goals from all users."""
    active_goals = services.goal_list_public(status_filter="active")
    
    return render(request, "goals/feed.html", {
        "goals": active_goals,
        "categories": Category.objects.all(),
    })


# =============================================================================
# AUTHENTICATION
# =============================================================================

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        if not username or not password:
            messages.error(request, "Username and password are required.")
            return redirect("login")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get("next")
            if next_url:
                return redirect(next_url)
            return redirect("index")
        else:
            messages.error(request, "Invalid username or password.")
            return redirect("login")
    
    return render(request, "goals/login.html")


def logout_view(request):
    logout(request)
    messages.success(request, "Successfully logged out.")
    return redirect("login")


def register_view(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password1")
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, "Registration successful.")
                return redirect("dashboard", username=user.username)
            else:
                messages.error(request, "Authentication failed after registration.")
    else:
        form = CustomUserCreationForm()
    
    return render(request, "goals/register.html", {"form": form})


# =============================================================================
# GOAL MANAGEMENT
# =============================================================================

def goals_view(request):
    return render(request, "goals/goals.html")


@login_required
def create_goal(request):
    """Create a new goal."""
    if request.method == "POST":
        form = GoalForm(request.POST)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.save()
            messages.success(request, "Goal created successfully!")
            return redirect("goal_detail", goal_id=goal.id)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = GoalForm()
    
    return render(request, "goals/create_goal.html", {"form": form})


@login_required
def edit_goal(request, goal_id):
    """Edit an existing goal."""
    goal = get_object_or_404(Goal, id=goal_id)
    
    if goal.user != request.user:
        messages.error(request, "You do not have permission to edit this goal.")
        return redirect("goal_detail", goal_id=goal.id)
    
    if request.method == "POST":
        form = GoalEditForm(request.POST, instance=goal)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.category = goal.category  # keep original
            goal.unit = goal.unit  # keep original
            goal.save()
            messages.success(request, "Goal updated successfully!")
            return redirect("goal_detail", goal_id=goal.id)
    else:
        form = GoalEditForm(instance=goal)
    
    return render(request, "goals/edit_goal.html", {"form": form, "goal": goal})


@login_required
def delete_goal(request, goal_id):
    """Delete a goal (owner only)."""
    if request.method == "POST":
        try:
            goal = Goal.objects.get(id=goal_id)
        except Goal.DoesNotExist:
            messages.error(request, "Goal not found.")
            return redirect("dashboard", username=request.user.username)
        
        if goal.user != request.user:
            messages.error(request, "You do not have permission to delete this goal.")
            return redirect("dashboard", username=request.user.username)
        
        goal.delete()
        messages.success(request, "Goal deleted successfully!")
        return redirect("dashboard", username=request.user.username)
    
    return redirect("dashboard", username=request.user.username)


# =============================================================================
# PROGRESS TRACKING
# =============================================================================

@login_required
def add_progress(request):
    """Add or update progress for a goal."""
    if request.method == "POST":
        goal_id = request.POST.get("goal_id")
        value = float(request.POST.get("progress"))
        goal = Goal.objects.get(id=goal_id)
        
        # Get uploaded images
        images = request.FILES.getlist("images")
        
        # Use service to create/update progress
        progress, created = services.progress_create_or_update(
            user=request.user,
            goal=goal,
            value=value,
            images=images
        )
        
        messages.success(request, "Progress saved successfully!")
        
        # Check if goal was just completed
        was_completed = services.progress_check_goal_completion(goal)
        if was_completed:
            messages.success(request, "Congratulations! You've achieved your goal.")
        
        return redirect("goal_detail", goal_id=goal_id)
    
    return redirect("dashboard", username=request.user.username)


# =============================================================================
# DASHBOARD & DETAIL VIEWS
# =============================================================================

@login_required
def dashboard(request, username):
    """User's personal dashboard."""
    goals = services.goal_list_for_user(user=request.user)
    categories = Category.objects.all()
    category_stats = services.dashboard_get_category_stats(user=request.user)
    
    return render(request, "goals/dashboard.html", {
        "user": request.user,
        "goals": goals,
        "categories": categories,
        "category_stats": category_stats,
    })


def goal_detail(request, goal_id):
    """Detailed view of a single goal with progress history and charts."""
    goal = get_object_or_404(
        Goal.objects.select_related('unit', 'category', 'user').prefetch_related('progresses'),
        id=goal_id
    )
    
    progress_history = goal.progresses.order_by("date")
    today_progress = goal.has_today_progress(request.user)
    
    # Get chart data from service
    chart_data = services.goal_get_chart_data(goal)
    
    return render(request, "goals/goal_detail.html", {
        "goal": goal,
        "today_progress": today_progress,
        "progress_history": progress_history,
        "chart_data": chart_data,
        "avg_per_day": chart_data["avg_per_day"],
        "needed_per_day": chart_data["needed_per_day"],
    })


def progress_history(request, goal_id):
    """View progress history for a goal."""
    goal = get_object_or_404(Goal, id=goal_id)
    progress_history = Progress.objects.filter(goal=goal).order_by("-date")
    
    return render(request, "goals/history.html", {
        "goal": goal,
        "progress_history": progress_history
    })


# =============================================================================
# AJAX/API ENDPOINTS
# =============================================================================

def load_units(request):
    """AJAX endpoint to load units for a category."""
    category_id = request.GET.get("category_id")
    units = Unit.objects.filter(categories__id=category_id).order_by("order")
    return JsonResponse(list(units.values("id", "name")), safe=False)


@login_required
def goals_api(request):
    """API endpoint to filter goals by status (for dynamic UI)."""
    filter_type = request.GET.get("status", "active")
    
    # Use service to get filtered goals
    filtered_goals = services.goal_list_for_user(
        user=request.user,
        status_filter=filter_type
    )
    
    html = render_to_string("goals/_goal_card.html", {
        "goals": filtered_goals,
        "show_progress_form": True
    }, request=request)
    
    return JsonResponse({"html": html})