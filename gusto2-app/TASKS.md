# General
Make App name clickable, the mealplan should be the homepage.

Tests?

# Mealplan
When clicking Get Rule-Based Suggestions, get different suggestions every time - the logic of the suggested meals itself shouldn't change.

Add an undo button which reloads the particular meal from notion

More requirements:
- Steak once a month

# Recipes



# Ordering
Add new Order page which has a list of meals for the next 7 days on the left hand side of the page. When clicking on a meal in the list, it should open a detail view on the right hand side that lists the ingredients for that meal. For now the ingredient list can be placeholder text.




-------
In the rule that checks whether meals are not planned more than once in 3 weeks, deeplink the violating meals to the recipes page, so when the meal is clicked in the violatino message it should go to the recipe page showing that recipe (and including all the meals planned for that recipe, which is already implemented).