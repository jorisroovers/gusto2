<template>
  <div class="recipe-list">
    <div class="recipe-controls">
      <div class="search-container">
        <input
          type="text"
          v-model="searchQuery"
          placeholder="Search recipes..."
          class="search-input"
        />
      </div>
      <button 
        @click="populateFromMeals" 
        class="populate-button"
        :disabled="loading"
      >
        Populate from Meal Plan
      </button>
    </div>

    <div v-if="notification" class="notification" :class="notificationType">
      {{ notification }}
    </div>

    <div v-if="loading" class="loading">Loading recipes...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="recipes.length === 0" class="no-recipes">No recipes found</div>
    <div v-else class="recipes-grid">
      <div v-for="recipe in filteredRecipes" 
           :key="recipe.Name" 
           :class="['recipe-card', { active: selectedRecipe && selectedRecipe.Name === recipe.Name }]"
           @click="selectRecipe(recipe)"
      >
        <h3>{{ recipe.Name }}</h3>
        <div class="tags" v-if="recipe.Tags">
          <span v-for="tag in recipe.Tags.split(',')" 
                :key="tag.trim()" 
                class="tag"
                :data-tag="tag.trim().toLowerCase()"
          >
            {{ tag.trim() }}
          </span>
        </div>
        <!-- Show associated meals when recipe is selected -->
        <div v-if="selectedRecipe && selectedRecipe.Name === recipe.Name && associatedMeals.length > 0" class="associated-meals">
          <h4>Used in meals:</h4>
          <div class="meals-list">
            <div v-for="meal in associatedMeals" 
                 :key="meal.Date + meal.Name" 
                 class="meal-item"
                 @click="goToMeal(meal)"
            >
              <div class="meal-date">{{ formatDate(meal.Date) }}</div>
              <div class="meal-name">{{ meal.Name }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'RecipeList',
  expose: ['fetchRecipes', 'populateFromMeals'],
  props: {
    selectedTags: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      recipes: [],
      loading: true,
      error: null,
      notification: '',
      notificationType: 'info',
      selectedRecipe: null,
      associatedMeals: [],
      searchQuery: ''
    };
  },
  computed: {
    filteredRecipes() {
      let filtered = this.recipes;
      
      // Filter by search query
      if (this.searchQuery) {
        const query = this.searchQuery.toLowerCase();
        filtered = filtered.filter(recipe => 
          recipe.Name.toLowerCase().includes(query)
        );
      }
      
      // Filter by tags
      if (this.selectedTags.length) {
        filtered = filtered.filter(recipe => {
          if (!recipe.Tags) return false;
          const recipeTags = recipe.Tags.split(',').map(t => t.trim().toLowerCase());
          return this.selectedTags.every(tag => recipeTags.includes(tag.toLowerCase()));
        });
      }
      
      return filtered;
    },
    allTags() {
      const tagSet = new Set();
      this.recipes.forEach(recipe => {
        if (recipe.Tags) {
          recipe.Tags.split(',')
            .map(t => t.trim())
            .filter(t => t)
            .forEach(tag => tagSet.add(tag));
        }
      });
      return Array.from(tagSet).sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase()));
    }
  },
  methods: {
    async fetchRecipes() {
      this.loading = true;
      this.error = null;
      try {
        const response = await axios.get('/api/recipes');
        if (response.data && response.data.recipes) {
          this.recipes = response.data.recipes;
          this.$parent.updateAvailableTags(this.allTags);
        } else {
          throw new Error('Unexpected response format');
        }
      } catch (error) {
        this.error = 'Failed to load recipes: ' + (error.response?.data?.detail || error.message);
      } finally {
        this.loading = false;
      }
    },
    async populateFromMeals() {
      this.loading = true;
      this.error = null;
      try {
        const response = await axios.post('/api/recipes/populate');
        this.recipes = response.data.recipes;
        this.$parent.updateAvailableTags(this.allTags);
        this.showNotification('Recipes populated from meal plan', 'success');
      } catch (error) {
        this.showNotification('Failed to populate recipes', 'error');
      } finally {
        this.loading = false;
      }
    },
    showNotification(message, type = 'info') {
      this.notification = message;
      this.notificationType = type;
      setTimeout(() => {
        this.notification = '';
      }, 3000);
    },
    async selectRecipe(recipe) {
      if (this.selectedRecipe && this.selectedRecipe.Name === recipe.Name) {
        this.selectedRecipe = null;
        this.associatedMeals = [];
        return;
      }
      
      this.selectedRecipe = recipe;
      try {
        const response = await axios.get('/api/meals');
        if (response.data && response.data.meals) {
          this.associatedMeals = response.data.meals.filter(meal => 
            meal.Name && meal.Name.trim() === recipe.Name.trim()
          );
        }
      } catch (error) {
        this.showNotification('Failed to fetch associated meals', 'error');
      }
    },
    formatDate(dateString) {
      if (!dateString) return '';
      const date = new Date(dateString);
      return date.toLocaleDateString();
    },
    goToMeal(meal) {
      // Navigate to meal plan page with the date as a query parameter
      this.$router.push({
        name: 'MealPlan',
        query: { date: meal.Date }
      });
    }
  },
  async mounted() {
    await this.fetchRecipes();
  }
};
</script>

<style scoped>
.recipe-list {
  width: 100%;
}

.recipe-controls {
  margin-bottom: 1.5rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.search-container {
  width: 100%;
  max-width: 400px;
}

.search-input {
  width: 100%;
  padding: 0.5rem 1rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.95rem;
  transition: border-color 0.2s ease;
}

.search-input:focus {
  outline: none;
  border-color: #3498db;
  box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2);
}

.populate-button {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  background-color: #3498db;
  color: white;
  border: 1px solid #2980b9;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 0.875rem;
}

.populate-button:hover:not(:disabled) {
  background-color: #2980b9;
}

.populate-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.recipes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1.5rem;
  margin-top: 1.5rem;
}

.recipe-card {
  background: white;
  border-radius: 8px;
  padding: 1.25rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  cursor: pointer;
}

.recipe-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.recipe-card.active {
  border: 2px solid #3498db;
}

.recipe-card h3 {
  margin: 0 0 1rem 0;
  color: #2c3e50;
  font-size: 1.1rem;
  line-height: 1.4;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.tag {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 500;
}

/* Diet tags */
.tag[data-tag*="vegetarisch"], .tag[data-tag*="vegan"] {
  background-color: #e8f5e9;
  color: #2e7d32;
}

.tag[data-tag*="glutten-free"], .tag[data-tag*="low fodmap"] {
  background-color: #f3e5f5;
  color: #7b1fa2;
}

/* Protein tags */
.tag[data-tag*="fish"], .tag[data-tag*="zalm"], .tag[data-tag*="tonijn"] {
  background-color: #e3f2fd;
  color: #1565c0;
}

.tag[data-tag*="meat"], .tag[data-tag*="chicken"], .tag[data-tag*="beef"], .tag[data-tag*="kip"], .tag[data-tag*="gehakt"], .tag[data-tag*="varken"], .tag[data-tag*="wild"] {
  background-color: #fce4ec;
  color: #c2185b;
}

/* Cuisine tags */
.tag[data-tag*="asian"], .tag[data-tag*="chinese"], .tag[data-tag*="thai"], .tag[data-tag*="indian"] {
  background-color: #fff3e0;
  color: #e65100;
}

.tag[data-tag*="italian"], .tag[data-tag*="italiaans"], .tag[data-tag*="mediteraans"] {
  background-color: #e8eaf6;
  color: #303f9f;
}

.tag[data-tag*="mexican"], .tag[data-tag*="mexicaans"], .tag[data-tag*="spanish"], .tag[data-tag*="spaans"] {
  background-color: #fff8e1;
  color: #ff6f00;
}

/* Cooking method tags */
.tag[data-tag*="bbq"], .tag[data-tag*="airfryer"] {
  background-color: #ffebee;
  color: #c62828;
}

.tag[data-tag*="lang koken"], .tag[data-tag*="ovenschotel"] {
  background-color: #ede7f6;
  color: #4527a0;
}

.tag[data-tag*="takeout"], .tag[data-tag*="restaurant"] {
  background-color: #e0f2f1;
  color: #00695c;
}

.tag[data-tag*="easy"], .tag[data-tag*="quick"] {
  background-color: #e1f5fe;
  color: #0277bd;
}

/* Carb/starch tags */
.tag[data-tag*="pasta"], .tag[data-tag*="noodles"], .tag[data-tag*="rijst"], .tag[data-tag*="rice"] {
  background-color: #f9fbe7;
  color: #827717;
}

.tag[data-tag*="aardappel"], .tag[data-tag*="potato"], .tag[data-tag*="puree"], .tag[data-tag*="friet"] {
  background-color: #fff3e0;
  color: #bf360c;
}

.tag[data-tag*="brood"] {
  background-color: #efebe9;
  color: #4e342e;
}

/* Vegetable tags */
.tag[data-tag*="brocolli"], .tag[data-tag*="spinazie"], .tag[data-tag*="bloemkool"], .tag[data-tag*="courgette"], .tag[data-tag*="pompoen"], .tag[data-tag*="salade"] {
  background-color: #f1f8e9;
  color: #558b2f;
}

/* Other characteristics */
.tag[data-tag*="vettig"], .tag[data-tag*="comfort"] {
  background-color: #fafafa;
  color: #424242;
}

/* Default style if no specific category matches */
.tag {
  background-color: #f5f5f5;
  color: #424242;
}

.loading, .error, .no-recipes {
  text-align: center;
  padding: 2.5rem;
  color: #666;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.error {
  color: #e74c3c;
  background-color: #fdf0f0;
}

.notification {
  padding: 0.75rem;
  margin-bottom: 1rem;
  border-radius: 5px;
  font-weight: 500;
  text-align: center;
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
}

.notification.success {
  background-color: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.notification.error {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.notification.info {
  background-color: #d1ecf1;
  color: #0c5460;
  border: 1px solid #bee5eb;
}

.associated-meals {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #eee;
}

.associated-meals h4 {
  margin: 0 0 0.75rem 0;
  color: #2c3e50;
  font-size: 0.95rem;
}

.meals-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.meal-item {
  padding: 0.75rem;
  background-color: #f8f9fa;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.meal-item:hover {
  background-color: #e9ecef;
}

.meal-date {
  color: #666;
  font-size: 0.8rem;
}

.meal-name {
  font-weight: 500;
  color: #2c3e50;
  font-size: 0.9rem;
}

@media (max-width: 768px) {
  .recipes-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }
}
</style>