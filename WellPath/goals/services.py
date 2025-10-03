"""
Business logic for goals app.
Following HackSoft Django Style Guide principles.
"""

from django.utils.timezone import now
from django.db.models import QuerySet
from datetime import timedelta, date
from typing import Dict, List, Optional, Tuple

from .models import Goal, Progress, ProgressPhoto, User
from taxonomy.models import Category


# =============================================================================
# GOAL STATUS & CALCULATIONS
# =============================================================================

def goal_is_completed(goal: Goal) -> bool:
    """
    Check if a goal has reached its target value.
    """
    return goal.get_current_value() >= goal.target_value


def goal_is_overdue(goal: Goal) -> bool:
    """
    Check if a goal is past its deadline and not completed.
    """
    if goal.deadline is None:
        return False
    return goal.deadline < now().date() and not goal_is_completed(goal)


def goal_get_status(goal: Goal) -> str:
    """
    Return goal status: 'completed', 'overdue', or 'active'.
    """
    if goal_is_completed(goal):
        return "completed"
    elif goal_is_overdue(goal):
        return "overdue"
    return "active"


def goal_progress_percentage(goal: Goal) -> float:
    """
    Calculate progress as a percentage (0-100).
    """
    total = goal.get_current_value()
    if goal.target_value == 0:
        return 0
    return min(100, (total / goal.target_value) * 100)


# =============================================================================
# PROGRESS MANAGEMENT
# =============================================================================

def progress_create_or_update(
    *,
    user: User,
    goal: Goal,
    value: float,
    date: Optional[date] = None,
    images: Optional[List] = None
) -> Tuple[Progress, bool]:
    """
    Create or update daily progress for a goal.
    Returns (progress, created) tuple.
    
    Args:
        user: The user adding progress
        goal: The goal to track progress for
        value: Progress value to record
        date: Date of progress (defaults to today)
        images: List of image files to attach
    
    Returns:
        Tuple of (Progress instance, bool indicating if newly created)
    """
    if date is None:
        date = now().date()
    
    progress, created = Progress.objects.get_or_create(
        user=user,
        goal=goal,
        date=date,
        defaults={"value": value}
    )
    
    if not created:
        progress.value = value
        progress.save()
    
    # Handle image uploads
    if images:
        for img in images:
            ProgressPhoto.objects.create(progress=progress, image=img)
    
    return progress, created


def progress_check_goal_completion(goal: Goal) -> bool:
    """
    Check if goal just got completed and update finished_at timestamp.
    Returns True if goal was just marked as completed.
    """
    if goal_is_completed(goal) and goal.finished_at is None:
        goal.finished_at = now()
        goal.save(update_fields=['finished_at'])
        return True
    return False


# =============================================================================
# GOAL QUERIES & FILTERING
# =============================================================================

def goal_list_for_user(
    *,
    user: User,
    status_filter: Optional[str] = None
) -> List[Goal]:
    """
    Get all goals for a user, optionally filtered by status.
    
    Args:
        user: User to get goals for
        status_filter: Optional filter - 'active', 'completed', or 'overdue'
    
    Returns:
        List of Goal objects
    """
    goals = Goal.objects.filter(
        user=user
    ).select_related(
        'unit', 'category'
    ).prefetch_related(
        'progresses'
    )
    
    # Convert to list and filter by status if needed
    goals_list = list(goals)
    
    if status_filter == "completed":
        return [g for g in goals_list if goal_get_status(g) == 'completed']
    elif status_filter == "overdue":
        return [g for g in goals_list if goal_get_status(g) == 'overdue']
    elif status_filter == "active":
        return [g for g in goals_list if goal_get_status(g) == 'active']
    
    return goals_list


def goal_list_public(*, status_filter: str = "active") -> List[Goal]:
    """
    Get public goals for feed, filtered by status.
    """
    all_goals = Goal.objects.filter(
        is_public=True
    ).select_related(
        'user', 'category', 'unit',
    ).prefetch_related(
        'likes', 'comments', 'progresses'
    )
    
    goals_list = list(all_goals)
    
    if status_filter == "active":
        return [g for g in goals_list if goal_get_status(g) == 'active']
    
    return goals_list


# =============================================================================
# DASHBOARD STATISTICS
# =============================================================================

def dashboard_get_category_stats(user: User) -> Dict[int, Dict]:
    """
    Calculate statistics for each category for a user's dashboard.
    
    Returns:
        Dict mapping category_id to stats dict with keys:
        - category: Category object
        - active: count of active goals
        - completed: count of completed goals
        - total: total goals in category
    """
    goals = list(Goal.objects.filter(
        user=user
    ).select_related(
        'unit', 'category'
    ).prefetch_related(
        'progresses'
    ))
    
    categories = Category.objects.all()
    category_stats = {}
    
    for category in categories:
        user_goals = [g for g in goals if g.category == category]
        category_stats[category.id] = {
            'category': category,
            'active': len([g for g in user_goals if goal_get_status(g) == 'active']),
            'completed': len([g for g in user_goals if goal_get_status(g) == 'completed']),
            'total': len(user_goals)
        }
    
    return category_stats


# =============================================================================
# CHART DATA GENERATION
# =============================================================================

def goal_get_chart_data(goal: Goal) -> Dict:
    """
    Generate chart data for goal detail page.
    Includes date range, values, cumulative progress, and averages.
    """
    progress_history = goal.progresses.order_by("date")
    
    # Determine date range
    if progress_history.exists():
        start_date = progress_history.first().date
    else:
        start_date = goal.created_at.date()
    
    end_date = goal.deadline or now().date()
    
    # Build full date range
    all_dates = []
    current = start_date
    while current <= end_date:
        all_dates.append(current)
        current += timedelta(days=1)
    
    # Map progress by date
    progress_map = {p.date: p.value for p in progress_history}
    
    # Build aligned lists
    cumulative = []
    values = []
    running_total = 0.0
    today = now().date()
    
    for d in all_dates:
        if d <= today:
            v = float(progress_map.get(d, 0))
            values.append(v)
            running_total += v
            cumulative.append(running_total)
        else:
            values.append(None)
            cumulative.append(None)
    
    # Calculate averages
    last_date = min(today, end_date)
    days_passed = (last_date - start_date).days + 1 if last_date >= start_date else 1
    
    total_progress = goal.get_current_value()
    avg_per_day = total_progress / days_passed if days_passed > 0 else 0
    
    # Calculate needed per day
    if goal.deadline and today <= goal.deadline:
        days_remaining = (goal.deadline - today).days + 1
    else:
        days_remaining = 0
    
    needed_per_day = 0
    if days_remaining > 0:
        needed_per_day = (goal.target_value - total_progress) / days_remaining
        needed_per_day = max(needed_per_day, 0)
    elif goal.target_value > total_progress:
        needed_per_day = goal.target_value - total_progress
    
    return {
        "dates": [d.strftime("%Y-%m-%d") for d in all_dates],
        "values": values,
        "cumulative": cumulative,
        "unit": goal.unit.name if goal.unit else "",
        "target": float(goal.target_value) if goal.target_value is not None else None,
        "avg_per_day": avg_per_day,
        "needed_per_day": needed_per_day,
    }