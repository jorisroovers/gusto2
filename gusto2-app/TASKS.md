Make App name clickable, the mealplan should be the homepage.

In the rule that checks whether meals are not planned more than once in 3 weeks, deeplink the violating meals to the recipes page, so when clicked the recipe page shows that recipe (and including all the meals planned for that recipe, which is already implemented).

Recipes should be auto-populated when loading meals, so that we don't have to explicitly click the populate from meal plan button.

When clicking Get Rule-Based Suggestions, get different suggestions every time - the logic of the suggested meals itself shouldn't change.

On the recipe page, add a "Suggest" button which should call a backend API endpoint which can for now just return some hardcoded recipe suggestion. On the front-end, there should be the ability to accept or reject the suggestion. 

Add an undo button which reloads the particular meal from notion

The suggest-recipe backend API should do an API call to chatGPT 4o to retrieve a recipe suggestion, similar in style to existing recipes. 
-> Perhaps try using https://openrouter.ai/ ?



More requirements:
- Steak once a month