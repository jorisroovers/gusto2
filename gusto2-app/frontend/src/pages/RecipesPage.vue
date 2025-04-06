<template>
  <div class="recipes-page">
    <div class="content-wrapper">
      <div class="recipes-layout">
        <div class="main-content">
          <div class="recipe-actions">
            <button @click="suggestRecipe" class="suggest-button">Suggest Recipe</button>
          </div>
          
          <!-- Recipe Suggestion -->
          <div v-if="currentSuggestion" class="recipe-suggestion">
            <h3>Suggested Recipe</h3>
            <div class="suggestion-content">
              <div class="suggestion-name">{{ currentSuggestion.name }}</div>
              <div class="suggestion-tags">
                <span v-for="tag in currentSuggestion.tags" 
                      :key="tag"
                      class="tag"
                      :data-tag="tag.toLowerCase()"
                >
                  {{ tag }}
                </span>
              </div>
              <div class="suggestion-actions">
                <button @click="acceptSuggestion" class="accept-button">Accept</button>
                <button @click="rejectSuggestion" class="reject-button">Reject</button>
              </div>
            </div>
          </div>

          <recipe-list ref="recipeList" :selectedTags="selectedTags" />
          <!-- Add filtered meals section -->
          <div v-if="selectedTags.length > 0 && filteredMeals.length > 0" class="filtered-meals">
            <h3>Meals with selected tags</h3>
            <div class="meals-list">
              <div 
                v-for="meal in filteredMeals" 
                :key="meal.Date + meal.Name" 
                class="meal-item"
                @click="goToMeal(meal)"
              >
                <div class="meal-date">{{ formatDate(meal.Date) }}</div>
                <div class="meal-name">{{ meal.Name }}</div>
                <div class="meal-tags">
                  <span v-for="tag in meal.Tags.split(',')" 
                        :key="tag.trim()" 
                        class="tag"
                        :data-tag="tag.trim().toLowerCase()"
                  >
                    {{ tag.trim() }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="tags-sidebar">
          <h3>Filter by Tags</h3>
          <div class="tags-list">
            <div 
              class="filter-tag no-tags-filter"
              :class="{ active: selectedTags.includes('NO_TAGS') }"
              @click="toggleTag('NO_TAGS')"
            >
              No tags
            </div>
            <div 
              v-for="tag in availableTags" 
              :key="tag"
              :class="['filter-tag', { active: selectedTags.includes(tag) }]"
              :data-tag="tag.toLowerCase()"
              @click="toggleTag(tag)"
            >
              {{ tag }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import RecipeList from '../components/RecipeList.vue';

export default {
  name: 'RecipesPage',
  components: {
    RecipeList
  },
  data() {
    return {
      selectedTags: [],
      availableTags: [],
      meals: [],
      currentSuggestion: null
    };
  },
  computed: {
    filteredMeals() {
      if (!this.selectedTags.length) return [];
      
      return this.meals.filter(meal => {
        if (!meal.Tags) return false;
        const mealTags = meal.Tags.split(',').map(t => t.trim().toLowerCase());
        return this.selectedTags.every(tag => mealTags.includes(tag.toLowerCase()));
      });
    }
  },
  methods: {
    toggleTag(tag) {
      const index = this.selectedTags.indexOf(tag);
      if (index === -1) {
        this.selectedTags.push(tag);
      } else {
        this.selectedTags.splice(index, 1);
      }
    },
    updateAvailableTags(tags) {
      this.availableTags = tags;
    },
    formatDate(dateString) {
      if (!dateString) return '';
      const date = new Date(dateString);
      return date.toLocaleDateString();
    },
    async fetchMeals() {
      try {
        const response = await axios.get('/api/meals');
        if (response.data && response.data.meals) {
          this.meals = response.data.meals;
        }
      } catch (error) {
        console.error('Error fetching meals:', error);
      }
    },
    goToMeal(meal) {
      // Navigate to meal plan page with the date as a query parameter
      this.$router.push({
        name: 'MealPlan',
        query: { date: meal.Date }
      });
    },
    async suggestRecipe() {
      try {
        const response = await axios.get('/api/suggest-recipe');
        if (response.data && response.data.recipe) {
          this.currentSuggestion = response.data.recipe;
        }
      } catch (error) {
        console.error('Error getting recipe suggestion:', error);
      }
    },
    async acceptSuggestion() {
      if (!this.currentSuggestion) return;
      
      try {
        await axios.post('/api/recipes', {
          Name: this.currentSuggestion.name,
          Tags: this.currentSuggestion.tags.join(', ')
        });
        this.currentSuggestion = null;
        // Refresh recipe list
        if (this.$refs.recipeList) {
          this.$refs.recipeList.fetchRecipes();
        }
      } catch (error) {
        console.error('Error accepting suggestion:', error);
      }
    },
    rejectSuggestion() {
      this.currentSuggestion = null;
    }
  },
  async mounted() {
    await this.fetchMeals();
  }
};
</script>

<style scoped>
.recipes-page {
  width: 100%;
  height: calc(100vh - 60px); /* Adjust height based on your header height */
}

.content-wrapper {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 1rem;
  height: 100%;
}

.recipes-layout {
  display: grid;
  grid-template-columns: 1fr 250px;
  gap: 2rem;
  align-items: start;
  height: 100%;
}

.main-content {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.filtered-meals {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.filtered-meals h3 {
  margin: 0 0 1rem 0;
  color: #2c3e50;
}

.meals-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.meal-item {
  padding: 1rem;
  background-color: #f8f9fa;
  border-radius: 6px;
  display: grid;
  gap: 0.5rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.meal-item:hover {
  background-color: #e9ecef;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.meal-date {
  color: #666;
  font-size: 0.875rem;
}

.meal-name {
  font-weight: 500;
  color: #2c3e50;
}

.meal-tags {
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

/* Tag color system for filtered meal tags */
.tag[data-tag*="vegetarian"], .tag[data-tag*="vegan"] {
  background-color: #e8f5e9;
  color: #2e7d32;
}

.tag[data-tag*="spicy"], .tag[data-tag*="hot"] {
  background-color: #fbe9e7;
  color: #d84315;
}

.tag[data-tag*="fish"], .tag[data-tag*="seafood"] {
  background-color: #e3f2fd;
  color: #1565c0;
}

.tag[data-tag*="meat"], .tag[data-tag*="chicken"], .tag[data-tag*="beef"], .tag[data-tag*="pork"] {
  background-color: #fce4ec;
  color: #c2185b;
}

.tag[data-tag*="quick"], .tag[data-tag*="easy"] {
  background-color: #f3e5f5;
  color: #7b1fa2;
}

.tag {
  /* Default tag style if no specific category matches */
  background-color: #f5f5f5;
  color: #424242;
}

.tags-sidebar {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  position: sticky;
  top: 2rem;
  max-height: calc(100vh - 100px); /* Adjust based on header + margins */
  overflow-y: auto;
}

.tags-sidebar h3 {
  margin: 0 0 1rem 0;
  color: #2c3e50;
  position: sticky;
  top: 0;
  background: white;
  padding-bottom: 0.5rem;
  z-index: 1;
}

.tags-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  overflow-y: auto;
}

.filter-tag {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

/* Diet tags */
.filter-tag[data-tag*="vegetarisch"], .filter-tag[data-tag*="vegan"] {
  background-color: #e8f5e9;
  color: #2e7d32;
}

.filter-tag[data-tag*="glutten-free"], .filter-tag[data-tag*="low fodmap"] {
  background-color: #f3e5f5;
  color: #7b1fa2;
}

/* Protein tags */
.filter-tag[data-tag*="fish"], .filter-tag[data-tag*="zalm"], .filter-tag[data-tag*="tonijn"] {
  background-color: #e3f2fd;
  color: #1565c0;
}

.filter-tag[data-tag*="meat"], .filter-tag[data-tag*="chicken"], .filter-tag[data-tag*="beef"], .filter-tag[data-tag*="kip"], .filter-tag[data-tag*="gehakt"], .filter-tag[data-tag*="varken"], .filter-tag[data-tag*="wild"] {
  background-color: #fce4ec;
  color: #c2185b;
}

/* Cuisine tags */
.filter-tag[data-tag*="asian"], .filter-tag[data-tag*="chinese"], .filter-tag[data-tag*="thai"], .filter-tag[data-tag*="indian"] {
  background-color: #fff3e0;
  color: #e65100;
}

.filter-tag[data-tag*="italian"], .filter-tag[data-tag*="italiaans"], .filter-tag[data-tag*="mediteraans"] {
  background-color: #e8eaf6;
  color: #303f9f;
}

.filter-tag[data-tag*="mexican"], .filter-tag[data-tag*="mexicaans"], .filter-tag[data-tag*="spanish"], .filter-tag[data-tag*="spaans"] {
  background-color: #fff8e1;
  color: #ff6f00;
}

/* Cooking method tags */
.filter-tag[data-tag*="bbq"], .filter-tag[data-tag*="airfryer"] {
  background-color: #ffebee;
  color: #c62828;
}

.filter-tag[data-tag*="lang koken"], .filter-tag[data-tag*="ovenschotel"] {
  background-color: #ede7f6;
  color: #4527a0;
}

.filter-tag[data-tag*="takeout"], .filter-tag[data-tag*="restaurant"] {
  background-color: #e0f2f1;
  color: #00695c;
}

.filter-tag[data-tag*="easy"], .filter-tag[data-tag*="quick"] {
  background-color: #e1f5fe;
  color: #0277bd;
}

/* Carb/starch tags */
.filter-tag[data-tag*="pasta"], .filter-tag[data-tag*="noodles"], .filter-tag[data-tag*="rijst"], .filter-tag[data-tag*="rice"] {
  background-color: #f9fbe7;
  color: #827717;
}

.filter-tag[data-tag*="aardappel"], .filter-tag[data-tag*="potato"], .filter-tag[data-tag*="puree"], .filter-tag[data-tag*="friet"] {
  background-color: #fff3e0;
  color: #bf360c;
}

.filter-tag[data-tag*="brood"] {
  background-color: #efebe9;
  color: #4e342e;
}

/* Vegetable tags */
.filter-tag[data-tag*="brocolli"], .filter-tag[data-tag*="spinazie"], .filter-tag[data-tag*="bloemkool"], .filter-tag[data-tag*="courgette"], .filter-tag[data-tag*="pompoen"], .filter-tag[data-tag*="salade"] {
  background-color: #f1f8e9;
  color: #558b2f;
}

/* Other characteristics */
.filter-tag[data-tag*="vettig"], .filter-tag[data-tag*="comfort"] {
  background-color: #fafafa;
  color: #424242;
}

/* Default style and active state */
.filter-tag {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s ease;
  background-color: #f5f5f5;
  color: #424242;
}

.filter-tag:hover {
  filter: brightness(0.95);
}

.filter-tag.active {
  filter: brightness(0.9);
  font-weight: 500;
}

/* No tags filter */
.no-tags-filter {
  background-color: #eceff1;
  color: #546e7a;
  border: 1px dashed #90a4ae;
  margin-bottom: 1rem;
}

.no-tags-filter:hover {
  background-color: #cfd8dc;
}

.no-tags-filter.active {
  background-color: #cfd8dc;
  border-style: solid;
}

.recipe-actions {
  margin-bottom: 1rem;
}

.suggest-button {
  background-color: #4CAF50;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
  transition: background-color 0.2s;
}

.suggest-button:hover {
  background-color: #45a049;
}

.recipe-suggestion {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  margin-bottom: 1.5rem;
}

.recipe-suggestion h3 {
  margin: 0 0 1rem 0;
  color: #2c3e50;
}

.suggestion-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.suggestion-name {
  font-size: 1.2rem;
  font-weight: 500;
  color: #2c3e50;
}

.suggestion-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.suggestion-actions {
  display: flex;
  gap: 1rem;
  margin-top: 0.5rem;
}

.accept-button, .reject-button {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.2s;
}

.accept-button {
  background-color: #4CAF50;
  color: white;
}

.accept-button:hover {
  background-color: #45a049;
}

.reject-button {
  background-color: #f44336;
  color: white;
}

.reject-button:hover {
  background-color: #da190b;
}

@media (max-width: 768px) {
  .recipes-layout {
    grid-template-columns: 1fr;
  }
  
  .tags-sidebar {
    position: static;
    margin-bottom: 2rem;
    max-height: none;
    overflow-y: visible;
  }
  
  .tags-list {
    flex-direction: row;
    flex-wrap: wrap;
    overflow-y: visible;
  }
  
  .tags-sidebar h3 {
    position: static;
  }
}
</style>