# weatherspoons
Basic recipe recommender app using flask, sqlite, and HTML. Hits two APIs to create suggestions.

From a group project for Boston University's CS411 class from Fall 2022. 

App includes GitHub OAuth and uses Geoapify, weather.gov, and Spoonacular APIs for recommendations. 

After a user enters their zipcode, Geoapify finds their approximate location. The location is then sent to the weather.gov API for the weather.
A vibe is assigned based on the weather, which is sent ot the Spoonacular API for a recipe recommendation.
