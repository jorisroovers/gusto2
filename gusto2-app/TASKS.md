# General
Tests?

Clean up the code, make it pass ruff.

Run ruff against the backend code, fix all issues so it passes.

# Mealplan

On the mealplan page, improve the left-hand page formatting and layout, especially the meal browsing experience. All features should remain, but it should look better and be more intuitive to use. Do not change the calendar UI on the right hand side.

When clicking Get Rule-Based Suggestions, get different suggestions every time - the logic of the suggested meals itself shouldn't change.

More requirements:
- Steak once a month

Fix comfort food friday, it's not working correctly


In the rule that checks for the reoccurrence of meals in 3 weeks, make it skip that check if the meal has an "Exclude rule" tag.

In the rule that checks whether meals are not planned more than once in 3 weeks, deeplink the violating meals to the recipes page, so when the meal is clicked in the violation message it should go to the recipe page showing that recipe (and including all the meals planned for that recipe, which is already implemented).

# Recipes

On the recipes page, allow for removal and addition of tags to recipes.

When clicking on suggest recipe, show a loading animation

https://github.com/hhursev/recipe-scrapers

https://www.ah.nl/allerhande/recepten-zoeken


# Ordering

Allow ingredients to be favorited, these should then be shown at the top or highlighted in some way.

Food replacements:
- Melk -> havermelk
- cheese -> vegan cheese
- 

Preferred brands:
- De Ceco, etc

Allow reloading of ingredients


-------
