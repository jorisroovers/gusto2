
On the recipe page, show all tags on the right hand side and allow filtering of the recipes based on one or more selected tags.

When filtering on tags in the recipe page, also show a list of the meals that have those tags.

When clicking Get Rule-Based Suggestions, get different suggestions every time - the logic of the suggested meals itself shouldn't change.

On the recipe page, add a "Suggest" button which should call a backend API endpoint which can for now just return some hardcoded recipe suggestion. On the front-end, there should be the ability to accept or reject the suggestion. 

The suggest-recipe backend API should do an API call to chatGPT 4o to retrieve a recipe suggestion, similar in style to existing recipes. 
-> Perhaps try using https://openrouter.ai/ ?



More requirements:
- Steak once a month