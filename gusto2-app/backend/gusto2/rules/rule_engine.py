"""
Rule engine for meal planning.

This module defines:
1. Data structures for constraints and requirements
2. Logic for validating meal plans against these rules
3. Functions to consider rules when suggesting new meals
"""

from datetime import datetime, timedelta
from enum import Enum, auto
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from collections import defaultdict


class RuleType(Enum):
    """Type of rule: constraint (cannot be violated) or requirement (should be met)."""
    CONSTRAINT = auto()
    REQUIREMENT = auto()


class RuleScope(Enum):
    """Scope of the rule: applies to a day, week, or other time period."""
    DAY = auto()
    WEEK = auto()
    SLIDING_WINDOW = auto()  # For rules like "don't repeat within 3 weeks"


class Rule:
    """Base class for meal planning rules."""
    
    def __init__(self, name: str, description: str, type: RuleType, scope: RuleScope, enabled: bool = True):
        self.name = name
        self.description = description
        self.type = type
        self.scope = scope
        self.enabled = enabled
    
    def validate(self, meals_df: pd.DataFrame, date: Optional[datetime] = None) -> Tuple[bool, str]:
        """
        Validate the rule against a meal plan.
        
        Args:
            meals_df: DataFrame containing meal plans
            date: Optional date to focus validation around
            
        Returns:
            Tuple of (is_valid, message)
        """
        raise NotImplementedError("Subclasses must implement validate()")
    
    def can_add_meal(self, meal_name: str, meal_tags: List[str], date: datetime, 
                     meals_df: pd.DataFrame) -> Tuple[bool, str]:
        """
        Check if adding a specific meal on a date would violate this rule.
        
        Args:
            meal_name: Name of the meal to add
            meal_tags: Tags associated with the meal
            date: Date to add the meal
            meals_df: Existing meal plan dataframe
            
        Returns:
            Tuple of (can_add, reason)
        """
        raise NotImplementedError("Subclasses must implement can_add_meal()")


class NoRepeatInWindowRule(Rule):
    """Don't repeat the same meal within a sliding window of days."""
    
    def __init__(self, name: str, description: str, window_days: int):
        super().__init__(
            name=name,
            description=description,
            type=RuleType.CONSTRAINT,
            scope=RuleScope.SLIDING_WINDOW
        )
        self.window_days = window_days
    
    def validate(self, meals_df: pd.DataFrame, date: Optional[datetime] = None) -> Tuple[bool, str]:
        """Check if any meals are repeated within the window."""
        if meals_df.empty:
            return True, "No meals to validate"
        
        # Ensure tags are case insensitive by converting to lowercase
        if 'Tags' in meals_df.columns:
            meals_df = meals_df.copy()
            meals_df['Tags'] = meals_df['Tags'].str.lower()
        
        # If no date specified, check the entire dataframe
        if date is None:
            meal_occurrences = defaultdict(list)
            
            # Ensure the Date column is in datetime format
            meals_df = meals_df.copy()
            meals_df['Date'] = pd.to_datetime(meals_df['Date'])
            
            # Sort by date
            meals_df = meals_df.sort_values('Date')
            
            # Check each meal
            for _, row in meals_df.iterrows():
                if pd.isna(row['Name']) or pd.isna(row['Date']):
                    continue
                
                meal_name = row['Name']
                meal_date = row['Date']
                
                # Check this meal against previous occurrences
                for prev_date in meal_occurrences[meal_name]:
                    days_diff = (meal_date - prev_date).days
                    
                    if 0 < days_diff <= self.window_days:
                        return False, f"'{meal_name}' repeats on {prev_date.strftime('%Y-%m-%d')} and {meal_date.strftime('%Y-%m-%d')}, which is within {days_diff} days (window is {self.window_days} days)"
                
                # Add this occurrence
                meal_occurrences[meal_name].append(meal_date)
            
            return True, "No meals repeat within the sliding window"
        else:
            # For a specific date, check just the window around it
            start_date = date - timedelta(days=self.window_days)
            end_date = date + timedelta(days=self.window_days)
            
            # Ensure the Date column is in datetime format
            meals_df = meals_df.copy()
            meals_df['Date'] = pd.to_datetime(meals_df['Date'])
            
            # Filter to the relevant date range
            window_meals = meals_df[(meals_df['Date'] >= start_date) & (meals_df['Date'] <= end_date)]
            
            # Count occurrences of each meal in the window
            meal_counts = window_meals['Name'].value_counts()
            
            # Check for repeats
            repeats = meal_counts[meal_counts > 1]
            if not repeats.empty:
                repeat_meals = repeats.index.tolist()
                return False, f"The following meals repeat within the {self.window_days}-day window around {date.strftime('%Y-%m-%d')}: {', '.join(repeat_meals)}"
            
            return True, "No meals repeat within the sliding window around the specified date"

    def can_add_meal(self, meal_name: str, meal_tags: List[str], date: datetime, 
                     meals_df: pd.DataFrame) -> Tuple[bool, str]:
        """Check if adding this meal would violate the no-repeat rule."""
        if meals_df.empty:
            return True, "No existing meals to check against"
        
        # Convert tags to lowercase
        meal_tags = [tag.lower() for tag in meal_tags] if meal_tags else []
        
        # Ensure the Date column is in datetime format
        meals_df = meals_df.copy()
        meals_df['Date'] = pd.to_datetime(meals_df['Date'])
        
        # Make a copy to avoid modifying the original dataframe
        if 'Tags' in meals_df.columns:
            meals_df['Tags'] = meals_df['Tags'].str.lower()
        
        # Get the window bounds
        start_date = date - timedelta(days=self.window_days)
        end_date = date + timedelta(days=self.window_days)
        
        # Filter to the relevant date range
        window_meals = meals_df[(meals_df['Date'] >= start_date) & 
                               (meals_df['Date'] <= end_date) & 
                               (meals_df['Name'] == meal_name)]
        
        if not window_meals.empty:
            first_occurrence = window_meals.iloc[0]
            days_diff = abs((date - pd.to_datetime(first_occurrence['Date'])).days)
            return False, f"'{meal_name}' already planned on {first_occurrence['Date'].strftime('%Y-%m-%d')}, which is only {days_diff} days away (window is {self.window_days} days)"
        
        return True, "Meal can be added without violating the sliding window constraint"


class WeeklyRequirementRule(Rule):
    """Require a specific tag to appear a minimum number of times in a week."""
    
    def __init__(self, name: str, description: str, tag: str, occurrences: int):
        super().__init__(
            name=name,
            description=description,
            type=RuleType.REQUIREMENT,
            scope=RuleScope.WEEK
        )
        # Store tag in lowercase to ensure case-insensitive comparison
        self.tag = tag.lower()
        self.occurrences = occurrences
    
    def validate(self, meals_df: pd.DataFrame, date: Optional[datetime] = None) -> Tuple[bool, str]:
        """Check if the tag appears the required number of times in the week."""
        if meals_df.empty:
            return False, f"No meals to validate for {self.tag} requirement"
        
        # Ensure the Date column is in datetime format
        meals_df = meals_df.copy()
        meals_df['Date'] = pd.to_datetime(meals_df['Date'])
        
        # If no date specified, group by ISO week and check each week
        if date is None:
            # Group by ISO week (Monday-based)
            meals_df['Week'] = meals_df['Date'].dt.isocalendar().week
            meals_df['Year'] = meals_df['Date'].dt.isocalendar().year
            
            # Each (year, week) tuple is a complete Monday-Sunday week
            weeks = meals_df.groupby(['Year', 'Week'])
            
            for (year, week), week_meals in weeks:
                # Count meals with the required tag
                tag_count = 0
                for _, row in week_meals.iterrows():
                    if pd.notna(row['Tags']):
                        meal_tags = [t.strip().lower() for t in row['Tags'].split(',')]
                        if self.tag in meal_tags:
                            tag_count += 1
                
                if tag_count < self.occurrences:
                    # Get Monday's date for this week
                    monday_date = week_meals['Date'].min().strftime('%Y-%m-%d')
                    return False, f"Week starting {monday_date} has only {tag_count} meals with tag '{self.tag}', but {self.occurrences} are required"
            
            return True, f"All weeks have at least {self.occurrences} meals with tag '{self.tag}'"
        else:
            # For a specific date, check just that ISO week (Monday-Sunday)
            iso_calendar = date.isocalendar()
            week_meals = meals_df[meals_df['Date'].dt.isocalendar().week == iso_calendar.week]
            
            # Count meals with the required tag
            tag_count = 0
            for _, row in week_meals.iterrows():
                if pd.notna(row['Tags']):
                    meal_tags = [t.strip().lower() for t in row['Tags'].split(',')]
                    if self.tag in meal_tags:
                        tag_count += 1
            
            if tag_count < self.occurrences:
                # Get Monday's date for this week
                week_start = date - timedelta(days=date.weekday())
                return False, f"Week starting {week_start.strftime('%Y-%m-%d')} has only {tag_count} meals with tag '{self.tag}', but {self.occurrences} are required"
            
            return True, f"Week has at least {self.occurrences} meals with tag '{self.tag}'"
    
    def can_add_meal(self, meal_name: str, meal_tags: List[str], date: datetime, 
                     meals_df: pd.DataFrame) -> Tuple[bool, str]:
        """
        Check how adding this meal affects the weekly requirement.
        Since this is a requirement not a constraint, it's always allowed to add a meal,
        but we return information about whether it helps meet the requirement.
        """
        # This is a requirement, not a constraint, so meals can always be added
        # But we'll check if it helps meet the requirement
        
        meal_tags = [t.lower() for t in meal_tags] if meal_tags else []
        
        if not meal_tags:
            return True, f"Meal doesn't have the '{self.tag}' tag, so doesn't help meet the weekly requirement"
        
        has_required_tag = self.tag in meal_tags
        
        if not has_required_tag:
            return True, f"Meal doesn't have the '{self.tag}' tag, so doesn't help meet the weekly requirement"
        
        # Ensure the Date column is in datetime format
        meals_df = meals_df.copy()
        meals_df['Date'] = pd.to_datetime(meals_df['Date'])
        
        # Get the ISO week for this date (Monday-based)
        iso_calendar = date.isocalendar()
        week_meals = meals_df[meals_df['Date'].dt.isocalendar().week == iso_calendar.week]
        
        # Count existing meals with the required tag
        tag_count = 0
        for _, row in week_meals.iterrows():
            if pd.notna(row['Tags']):
                week_meal_tags = [t.strip().lower() for t in row['Tags'].split(',')]
                if self.tag in week_meal_tags:
                    tag_count += 1
        
        if tag_count >= self.occurrences:
            return True, f"Weekly requirement for '{self.tag}' ({self.occurrences} meals) already met ({tag_count} meals)"
        else:
            # This meal would help meet the requirement
            return True, f"Adding this meal helps meet the weekly requirement for '{self.tag}' ({tag_count + 1}/{self.occurrences})"


class SpecificDayRequirementRule(Rule):
    """Require a specific tag on a specific day of the week."""
    
    def __init__(self, name: str, description: str, day_of_week: int, tag: str):
        super().__init__(
            name=name,
            description=description,
            type=RuleType.REQUIREMENT,
            scope=RuleScope.DAY
        )
        self.day_of_week = day_of_week
        # Store tag in lowercase to ensure case-insensitive comparison
        self.tag = tag.lower()
    
    def validate(self, meals_df: pd.DataFrame, date: Optional[datetime] = None) -> Tuple[bool, str]:
        """Check if the specified day has a meal with the required tag."""
        if meals_df.empty:
            return False, f"No meals to validate for {self.tag} on {self._day_name()} requirement"
        
        # Ensure the Date column is in datetime format
        meals_df = meals_df.copy()
        meals_df['Date'] = pd.to_datetime(meals_df['Date'])
        
        # If no date specified, check all instances of the specified day
        if date is None:
            # Filter to the relevant day of week
            day_meals = meals_df[meals_df['Date'].dt.weekday == self.day_of_week]
            
            if day_meals.empty:
                return False, f"No meals found for {self._day_name()}"
            
            # Group by week
            day_meals['Week'] = day_meals['Date'].dt.isocalendar().week
            day_meals['Year'] = day_meals['Date'].dt.isocalendar().year
            
            # Check each instance of the day
            for (year, week), day_instance in day_meals.groupby(['Year', 'Week']):
                has_tag = False
                for _, row in day_instance.iterrows():
                    if pd.notna(row['Tags']):
                        meal_tags = [t.strip().lower() for t in row['Tags'].split(',')]
                        if self.tag in meal_tags:
                            has_tag = True
                            break
                
                if not has_tag:
                    instance_date = day_instance.iloc[0]['Date'].strftime('%Y-%m-%d')
                    return False, f"{self._day_name()} on {instance_date} doesn't have a meal with tag '{self.tag}'"
            
            return True, f"All {self._day_name()}s have a meal with tag '{self.tag}'"
        else:
            # For a specific date, check only if it's the required day
            if date.weekday() != self.day_of_week:
                return True, f"Date {date.strftime('%Y-%m-%d')} is not a {self._day_name()}, so this rule doesn't apply"
            
            # Filter to just this date
            day_meal = meals_df[meals_df['Date'] == date]
            
            if day_meal.empty:
                return False, f"No meal found for {date.strftime('%Y-%m-%d')}"
            
            has_tag = False
            for _, row in day_meal.iterrows():
                if pd.notna(row['Tags']):
                    meal_tags = [t.strip().lower() for t in row['Tags'].split(',')]
                    if self.tag in meal_tags:
                        has_tag = True
                        break
            
            if not has_tag:
                return False, f"{self._day_name()} on {date.strftime('%Y-%m-%d')} doesn't have a meal with tag '{self.tag}'"
            
            return True, f"{self._day_name()} has a meal with tag '{self.tag}'"

    def can_add_meal(self, meal_name: str, meal_tags: List[str], date: datetime, 
                     meals_df: pd.DataFrame) -> Tuple[bool, str]:
        """
        Check if adding this meal would help meet the day-specific requirement.
        Since this is a requirement not a constraint, it's always allowed,
        but we return information about whether it helps meet the requirement.
        """
        # If it's not the required day, this rule doesn't apply
        if date.weekday() != self.day_of_week:
            return True, f"Date is not a {self._day_name()}, so rule for '{self.tag}' doesn't apply"
        
        # Check if the meal has the required tag
        meal_tags = [t.lower() for t in meal_tags] if meal_tags else []
        has_required_tag = self.tag in meal_tags
        
        if has_required_tag:
            return True, f"Meal has the '{self.tag}' tag, which is required for {self._day_name()}"
        else:
            return True, f"Meal doesn't have the '{self.tag}' tag, which is recommended for {self._day_name()}"
    
    def _day_name(self) -> str:
        """Get the name of the day of week."""
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        return days[self.day_of_week]


class RuleEngine:
    """Engine to manage and evaluate mealplan rules."""
    
    def __init__(self):
        self.rules: List[Rule] = []
    
    def add_rule(self, rule: Rule) -> None:
        """Add a rule to the engine."""
        self.rules.append(rule)
    
    def get_rules(self) -> List[Rule]:
        """Get all rules."""
        return self.rules
    
    def get_enabled_rules(self) -> List[Rule]:
        """Get only enabled rules."""
        return [rule for rule in self.rules if rule.enabled]
    
    def validate_meal_plan(self, meals_df: pd.DataFrame, date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Validate a meal plan against all enabled rules.
        
        Args:
            meals_df: DataFrame containing meal plans
            date: Optional date to focus validation around
            
        Returns:
            List of validation results, each with rule info and validation status
        """
        results = []
        
        for rule in self.get_enabled_rules():
            is_valid, message = rule.validate(meals_df, date)
            
            results.append({
                "rule_name": rule.name,
                "rule_description": rule.description,
                "rule_type": rule.type.name,
                "rule_scope": rule.scope.name,
                "is_valid": is_valid,
                "message": message
            })
        
        return results
    
    def can_add_meal(self, meal_name: str, meal_tags: List[str], date: datetime, 
                    meals_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Check if a meal can be added without violating constraints, and how it affects requirements.
        
        Args:
            meal_name: Name of the meal to add
            meal_tags: Tags for the meal
            date: Date to add the meal
            meals_df: Existing meal plan dataframe
            
        Returns:
            Dictionary with validation results
        """
        constraint_results = []
        requirement_results = []
        
        for rule in self.get_enabled_rules():
            can_add, reason = rule.can_add_meal(meal_name, meal_tags, date, meals_df)
            
            result = {
                "rule_name": rule.name,
                "can_add": can_add,
                "reason": reason
            }
            
            if rule.type == RuleType.CONSTRAINT:
                constraint_results.append(result)
            else:  # REQUIREMENT
                requirement_results.append(result)
        
        # A meal can be added if it doesn't violate any constraints
        all_constraints_satisfied = all(result["can_add"] for result in constraint_results)
        
        return {
            "can_add": all_constraints_satisfied,
            "constraint_results": constraint_results,
            "requirement_results": requirement_results
        }
    
    def suggest_meals_for_date(self, date: datetime, available_meals: List[Dict[str, Any]], 
                              meals_df: pd.DataFrame, count: int = 3) -> List[Dict[str, Any]]:
        """
        Suggest meals for a date that satisfy constraints and best meet requirements.
        
        Args:
            date: Date to suggest meals for
            available_meals: List of available meals, each with 'name' and 'tags'
            meals_df: Existing meal plan dataframe
            count: Number of suggestions to return
            
        Returns:
            List of suggested meals, ranked by how well they meet requirements
        """
        suggestions = []
        
        import random
        # Shuffle available meals first to introduce initial randomness
        available_meals = available_meals.copy()
        random.shuffle(available_meals)
        
        for meal in available_meals:
            meal_name = meal['name']
            meal_tags = meal.get('tags', '').split(',') if meal.get('tags') else []
            
            # Check if this meal can be added
            result = self.can_add_meal(meal_name, meal_tags, date, meals_df)
            
            if result["can_add"]:
                # Calculate a score based on how many requirements it helps meet
                requirement_score = sum(1 for req in result["requirement_results"] 
                                      if "helps meet" in req["reason"])
                
                suggestions.append({
                    "meal": meal,
                    "requirement_score": requirement_score,
                    "validation_result": result
                })
        
        # Group suggestions by score
        score_groups = {}
        for suggestion in suggestions:
            score = suggestion["requirement_score"]
            if score not in score_groups:
                score_groups[score] = []
            score_groups[score].append(suggestion)
        
        # Shuffle each group of same-scored suggestions
        for score in score_groups:
            random.shuffle(score_groups[score])
        
        # Reconstruct the suggestions list maintaining score order but with shuffled same-score items
        suggestions = []
        for score in sorted(score_groups.keys(), reverse=True):
            suggestions.extend(score_groups[score])
        
        # Return the top suggestions
        return suggestions[:count]


# Create a default instance with common rules
default_rule_engine = RuleEngine()

# Add default rules
default_rule_engine.add_rule(
    NoRepeatInWindowRule(
        name="No repeat within 3 weeks",
        description="Don't plan the same meal twice in a 3 week sliding window",
        window_days=21
    )
)

default_rule_engine.add_rule(
    WeeklyRequirementRule(
        name="Weekly fish",
        description="Have fish at least once a week",
        tag="fish",
        occurrences=1
    )
)

default_rule_engine.add_rule(
    WeeklyRequirementRule(
        name="Weekly rice",
        description="Have rice at least once a week",
        tag="rice",
        occurrences=1
    )
)

default_rule_engine.add_rule(
    WeeklyRequirementRule(
        name="Weekly pasta",
        description="Have pasta at least once a week",
        tag="pasta",
        occurrences=1
    )
)

default_rule_engine.add_rule(
    SpecificDayRequirementRule(
        name="Friday comfort food",
        description="Friday = indulging = comfort food",
        day_of_week=4,  # 0 is Monday, so 4 is Friday
        tag="comfort food"
    )
)