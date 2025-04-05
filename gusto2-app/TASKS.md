Make App name clickable, the mealplan should be the homepage.



When clicking Get Rule-Based Suggestions, get different suggestions every time - the logic of the suggested meals itself shouldn't change.

On the recipe page, add a "Suggest" button which should call a backend API endpoint which can for now just return some hardcoded recipe suggestion. On the front-end, there should be the ability to accept or reject the suggestion. The suggested recipe should come with associated tags.

Add an undo button which reloads the particular meal from notion

The suggest-recipe backend API should do an API call to chatGPT 4o to retrieve a recipe suggestion, similar in style to existing recipes. 
-> Perhaps try using https://openrouter.ai/ ?



More requirements:
- Steak once a month


Add new Order page which has a list of meals for the next 7 days. 


-------
In the rule that checks whether meals are not planned more than once in 3 weeks, deeplink the violating meals to the recipes page, so when the meal is clicked in the violatino message it should go to the recipe page showing that recipe (and including all the meals planned for that recipe, which is already implemented).