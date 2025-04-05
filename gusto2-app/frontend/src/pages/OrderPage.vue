<template>
  <div class="order-page">
    <h2 class="page-title">Shopping Order</h2>
    
    <div class="order-layout">
      <!-- Left side: Meal list for next 7 days -->
      <div class="meal-list-container">
        <h3>Next 7 Days Meals</h3>
        <div v-if="loading" class="loading">Loading meals...</div>
        <div v-else-if="error" class="error">{{ error }}</div>
        <div v-else-if="upcomingMeals.length === 0" class="no-meals">No upcoming meals found</div>
        <div v-else class="meal-list">
          <div 
            v-for="meal in upcomingMeals" 
            :key="meal.Date"
            class="meal-item"
            :class="{ active: selectedMeal && selectedMeal.Date === meal.Date }"
            @click="selectMeal(meal)"
          >
            <div class="meal-date">{{ formatDate(meal.Date) }}</div>
            <div v-if="meal.Name" class="meal-name">{{ meal.Name }}</div>
            <div v-else class="no-meal-planned">No meal planned</div>
          </div>
        </div>
      </div>
      
      <!-- Right side: Selected meal details with ingredients -->
      <div class="meal-details-container">
        <div v-if="!selectedMeal" class="no-selection">
          <p>Select a meal from the list to view ingredients</p>
        </div>
        <div v-else class="meal-details">
          <h3>{{ selectedMeal.Name || 'No meal planned' }}</h3>
          
          <div v-if="selectedMeal.Tags" class="meal-tags">
            <div class="tags-container">
              <span 
                v-for="tag in selectedMeal.Tags.split(',')" 
                :key="tag.trim()" 
                class="tag"
                :data-tag="tag.trim().toLowerCase()"
              >
                {{ tag.trim() }}
              </span>
            </div>
          </div>
          
          <div v-if="selectedMeal.Notes" class="meal-notes">
            <h4>Notes:</h4>
            <p>{{ selectedMeal.Notes }}</p>
          </div>
          
          <div class="ingredients-section">
            <h4>Ingredients:</h4>
            <!-- Placeholder ingredients - will be replaced with real data later -->
            <ul class="ingredients-list">
              <li v-for="(ingredient, index) in getPlaceholderIngredients()" :key="index">
                {{ ingredient }}
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'OrderPage',
  data() {
    return {
      meals: [],
      upcomingMeals: [],
      selectedMeal: null,
      loading: true,
      error: null
    };
  },
  methods: {
    async fetchMeals() {
      this.loading = true;
      this.error = null;
      try {
        const response = await axios.get('/api/meals');
        if (response.data && response.data.meals) {
          this.meals = response.data.meals;
          this.filterUpcomingMeals();
        } else {
          this.error = 'No meals data found';
        }
      } catch (error) {
        this.error = 'Error fetching meals from backend';
        console.error('Error fetching meals:', error);
      } finally {
        this.loading = false;
      }
    },
    
    filterUpcomingMeals() {
      // Get today's date at midnight
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      
      // Filter meals for the next 7 days
      this.upcomingMeals = this.meals
        .filter(meal => {
          if (!meal.Date) return false;
          
          const mealDate = new Date(meal.Date);
          mealDate.setHours(0, 0, 0, 0);
          
          // Calculate days difference
          const timeDiff = mealDate - today;
          const daysDiff = timeDiff / (1000 * 3600 * 24);
          
          // Include meals from today (day 0) to 6 days from now (total 7 days)
          return daysDiff >= 0 && daysDiff < 7;
        })
        .sort((a, b) => new Date(a.Date) - new Date(b.Date));
      
      // Select the first meal by default if available
      if (this.upcomingMeals.length > 0) {
        this.selectMeal(this.upcomingMeals[0]);
      }
    },
    
    selectMeal(meal) {
      this.selectedMeal = meal;
    },
    
    formatDate(dateString) {
      if (!dateString) return '';
      const date = new Date(dateString);
      const options = { weekday: 'short', month: 'short', day: 'numeric' };
      return date.toLocaleDateString(undefined, options);
    },
    
    getPlaceholderIngredients() {
      // If no meal is selected, return empty array
      if (!this.selectedMeal || !this.selectedMeal.Name) {
        return [];
      }
      
      // Generate some placeholder ingredients based on the meal name
      // This will be replaced with real ingredients from the backend later
      const basicIngredients = [
        '500g mixed vegetables',
        '2 tablespoons olive oil',
        '1 onion, chopped',
        '2 cloves garlic, minced',
        'Salt and pepper to taste',
        'Fresh herbs (optional)'
      ];
      
      const proteinIngredients = [];
      
      // Add protein based on tags or meal name
      const mealNameLower = this.selectedMeal.Name.toLowerCase();
      const tags = this.selectedMeal.Tags ? this.selectedMeal.Tags.toLowerCase() : '';
      
      if (mealNameLower.includes('chicken') || tags.includes('chicken') || tags.includes('kip')) {
        proteinIngredients.push('500g chicken breast, diced');
      } else if (mealNameLower.includes('beef') || tags.includes('beef') || tags.includes('gehakt')) {
        proteinIngredients.push('500g ground beef');
      } else if (mealNameLower.includes('fish') || mealNameLower.includes('salmon') || 
                tags.includes('fish') || tags.includes('zalm')) {
        proteinIngredients.push('500g salmon fillet');
      } else if (tags.includes('vegetarisch') || tags.includes('vegan')) {
        proteinIngredients.push('250g tofu, cubed');
        proteinIngredients.push('1 can chickpeas, drained');
      } else {
        // Default protein
        proteinIngredients.push('500g protein of choice');
      }
      
      // Add starch based on tags or meal name
      const starchIngredients = [];
      if (mealNameLower.includes('pasta') || tags.includes('pasta')) {
        starchIngredients.push('350g pasta');
      } else if (mealNameLower.includes('rice') || tags.includes('rice') || tags.includes('rijst')) {
        starchIngredients.push('2 cups rice');
      } else if (mealNameLower.includes('potato') || tags.includes('potato') || tags.includes('aardappel')) {
        starchIngredients.push('4 large potatoes');
      } else {
        // Default starch
        starchIngredients.push('Side dish of choice');
      }
      
      return [...proteinIngredients, ...starchIngredients, ...basicIngredients];
    }
  },
  async mounted() {
    await this.fetchMeals();
  }
};
</script>

<style scoped>
.order-page {
  width: 100%;
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 1rem;
}

.page-title {
  text-align: center;
  margin-bottom: 2rem;
  color: #2c3e50;
}

.order-layout {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

/* Meal list styling */
.meal-list-container {
  flex: 1;
  min-width: 0;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  padding: 1.5rem;
}

.meal-list-container h3 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: #2c3e50;
  text-align: center;
}

.meal-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.meal-item {
  display: flex;
  flex-direction: column;
  padding: 12px;
  border-radius: 6px;
  border: 1px solid #e9ecef;
  cursor: pointer;
  transition: all 0.2s ease;
}

.meal-item:hover {
  background-color: #f8f9fa;
  border-color: #dee2e6;
}

.meal-item.active {
  background-color: #e3f2fd;
  border-color: #90caf9;
}

.meal-date {
  font-weight: 500;
  color: #6c757d;
  font-size: 0.875rem;
}

.meal-name {
  font-weight: 600;
  color: #212529;
  margin-top: 4px;
}

.no-meal-planned {
  color: #adb5bd;
  font-style: italic;
  margin-top: 4px;
}

/* Meal details styling */
.meal-details-container {
  flex: 1;
  min-width: 0;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  padding: 1.5rem;
  min-height: 300px;
}

.no-selection {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #6c757d;
  font-style: italic;
}

.meal-details h3 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: #2c3e50;
  text-align: center;
}

.meal-notes {
  margin-bottom: 1.5rem;
}

.meal-notes h4 {
  margin-bottom: 0.5rem;
  color: #495057;
}

.meal-notes p {
  margin: 0;
  color: #6c757d;
}

.ingredients-section h4 {
  margin-bottom: 0.5rem;
  color: #495057;
}

.ingredients-list {
  list-style-type: none;
  padding: 0;
  margin: 0;
}

.ingredients-list li {
  padding: 8px 0;
  border-bottom: 1px solid #f1f3f5;
  color: #495057;
}

.ingredients-list li:last-child {
  border-bottom: none;
}

/* Tag styling (copied from MealPlanPage.vue) */
.meal-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin: 0.5rem 0 1rem;
}

.tags-container {
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
  background-color: #f5f5f5;
  color: #424242;
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

/* Desktop layout */
@media (min-width: 768px) {
  .order-layout {
    flex-direction: row;
  }
  
  .meal-list-container {
    width: 40%;
  }
  
  .meal-details-container {
    width: 60%;
  }
}
</style>