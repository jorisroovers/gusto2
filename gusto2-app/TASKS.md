Recipes and Meal Plan should be different pages in the app which have different URIs.

Extract the css styles to a separate file.

On desktop, move to a full page width design, with app name and page links in a top navigation bar.

On desktop, In the mealplan page, move the calendar view to the right of the day view.

Brainstorm how we can implement a system for "mealplan rules":
- Constraints: cannot be violated
  Examples:
    - Don’t plan the same meal twice in a 3 week sliding window
- Requirements: must be met
  Examples:
    - On a weekly basis
        - Have fish at least once a week
        - Have rice at least once a week
        - Have pasta once a week
        - Friday = indulging = comfort food

The idea should then be that we:
1.  can validate that these conditions are met for any given week (but this should be able to be ignored, it's just validation not enforced)
2.  When new meals are suggested, it should not violate any of the constraints while also trying to meet the requirements for the week.


On the recipe page, add a "Suggest" button which should call a backend API endpoint which can for now just return some hardcoded recipe suggestion. On the front-end, there should be the ability to accept or reject the suggestion. 

The suggest-recipe backend API should do an API call to chatGPT 4o to retrieve a recipe suggestion, similar in style to existing recipes. 
-> Perhaps try using https://openrouter.ai/ ?


