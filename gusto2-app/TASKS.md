# General
Tests?

Clean up the code, make it pass ruff.

Run ruff against the backend code, fix all issues so it passes.

In the database, meals should just be pointing to the recipe, rather than maintaining a separate copy of the meal and tags all together. This way data is not duplicated and when editing the tags of a meal or the meal itself, the recipe is updated everywhere instead of only for that day.

# Mealplan

When there's an unplanned meal in the weekend, it's not showing as red in the front-end. 

On the mealplan page, improve the left-hand page formatting and layout, especially the meal browsing experience. All features should remain, but it should look better and be more intuitive to use. Do not change the calendar UI on the right hand side.


When clicking Get Rule-Based Suggestions, get different suggestions every time - the logic of the suggested meals itself shouldn't change.

More requirements:
- Steak once a month

Fix comfort food friday, it's not working correctly

In the rule that checks whether meals are not planned more than once in 3 weeks, deeplink the violating meals to the recipes page, so when the meal is clicked in the violation message it should go to the recipe page showing that recipe (and including all the meals planned for that recipe, which is already implemented).

# Recipes

When clicking on suggest recipe, show a loading animation

https://github.com/hhursev/recipe-scrapers

https://www.ah.nl/allerhande/recepten-zoeken


# Ordering

Preferred brands:
- De Ceco, etc

Allow reloading of ingredients


-------
