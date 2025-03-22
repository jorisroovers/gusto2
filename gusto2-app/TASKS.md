In the calendar, add an extra column after sunday that is used to indicate the validation of that past week. It should show a green square with a check if all validations passed for that week and a red square with the number of failing validations in it otherwise. When the box is clicked, the validations for that week should be displayed.

Display tags of the selected meal.

In the calendar, still display days of other previous or next months if they are part of the week that has days in the current month. Shade those days a bit grayer so it's clear those days are not part of the current month.

In the meal edit screen, the tag field should auto-complete tags and show tags as labels that can be removed again inside the input field.

On the recipe page, show all tags on the right hand side and allow filtering of the recipes based on one or more selected tags.

On the recipe page, add a "Suggest" button which should call a backend API endpoint which can for now just return some hardcoded recipe suggestion. On the front-end, there should be the ability to accept or reject the suggestion. 

The suggest-recipe backend API should do an API call to chatGPT 4o to retrieve a recipe suggestion, similar in style to existing recipes. 
-> Perhaps try using https://openrouter.ai/ ?


