# General
Make App name clickable, the mealplan should be the homepage.

Tests?

# Mealplan


When clicking Get Rule-Based Suggestions, get different suggestions every time - the logic of the suggested meals itself shouldn't change.

On the mealplan page, add an undo button which reloads the particular meal from notion

More requirements:
- Steak once a month

In the rule that checks whether meals are not planned more than once in 3 weeks, deeplink the violating meals to the recipes page, so when the meal is clicked in the violatino message it should go to the recipe page showing that recipe (and including all the meals planned for that recipe, which is already implemented).

Change the mealplan rule that checks for weekly rice to checking for the 'asian' or 'rice' tags.

# Recipes



# Ordering

On the ordering page, when clicking a meal, use the OpenAI API to get a list of ingredients for that meal. Only fetch the ingredients when clicking on a meal (show a spinner while waiting). Ensure that once fetched, these ingredients are persisted through page reloads. 
Re-use the environment variables that are used for recipe suggestions for connecting to OpenAI. 

The prompt to get the ingredients should include:
- The ingredients should be available for purchase at the dutch Albert Heijn supermarket.  
- Not to include common base ingredient like salt, pepper, oil, etc. 
- Not to include amounts, only the ingredients themselves


On the ordering page, for each ingredient use the `supermarktconnector` python package, specifically `supermarktconnector.ah` to search for the particular ingredient on the Albert Heijn website. When results are are found, select the best match and then put the title of the found match in parentheses next to the ingredient name on the front-end.

-------
