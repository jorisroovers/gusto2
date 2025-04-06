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
            <div class="ingredients-header">
              <h4>Ingredients:</h4>
              <button 
                v-if="currentIngredients.length > 0" 
                @click="reloadIngredients"
                class="btn-reload-ingredients"
                :disabled="ingredientsLoading"
                title="Check AI again for ingredients"
              >
                <span v-if="!ingredientsLoading">Reload</span>
                <span v-else>Loading...</span>
              </button>
            </div>
            <!-- Ingredients with loading state -->
            <div v-if="ingredientsLoading" class="ingredients-loading">
              <div class="loading-spinner"></div>
              <p>Fetching ingredients...</p>
            </div>
            <ul v-else-if="currentIngredients.length > 0" class="ingredients-list">
              <li 
                v-for="(ingredient, index) in currentIngredients" 
                :key="index"
                @click="toggleProductSuggestions(ingredient)"
                :class="{ 'active': activeIngredient === ingredient }"
              >
                <div class="ingredient-row">
                  <span class="ingredient-name">{{ ingredient }}</span>
                  <span class="ingredient-action">
                    <i v-if="activeIngredient === ingredient" class="chevron up"></i>
                    <i v-else class="chevron down"></i>
                  </span>
                </div>
                <div v-if="activeIngredient === ingredient" class="product-suggestions">
                  <div v-if="productLoading" class="loading-products">
                    <div class="loading-spinner small"></div>
                    <span>Loading products...</span>
                  </div>
                  <div v-else-if="currentProducts.length === 0" class="no-products">
                    No products found for this ingredient
                  </div>
                  <div v-else class="products-container">
                    <div 
                      v-for="product in currentProducts" 
                      :key="product.id" 
                      class="product-card"
                      @click.stop="openProductUrl(product.url)"
                    >
                      <div class="product-image">
                        <img v-if="product.image_url" :src="product.image_url" :alt="product.name">
                        <div v-else class="no-image">No image</div>
                      </div>
                      <div class="product-info">
                        <div class="product-name">{{ product.name }}</div>
                        <div class="product-price">
                          <span>€{{ formatPrice(product.price) }}</span>
                          <span v-if="product.unit_price" class="unit-price">{{ product.unit_price }}</span>
                        </div>
                        <div v-if="product.bonus" class="bonus-label">BONUS</div>
                      </div>
                    </div>
                  </div>
                </div>
              </li>
            </ul>
            <div v-else-if="ingredientsFetchAttempted" class="no-ingredients">
              <p>No ingredients found for this meal.</p>
              <button class="btn-retry" @click="fetchIngredients">Try Again</button>
            </div>
            <div v-else class="click-to-fetch">
              <button class="btn-fetch-ingredients" @click="fetchIngredients">
                Load Ingredients
              </button>
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
  name: 'OrderPage',
  data() {
    return {
      meals: [],
      upcomingMeals: [],
      selectedMeal: null,
      loading: true,
      error: null,
      mealIngredients: {}, // Store ingredients for each meal
      ingredientsLoading: false,
      ingredientsFetchAttempted: false,
      activeIngredient: null, // Currently selected ingredient for product suggestions
      productCache: {}, // Cache for product suggestions
      productLoading: false,
      currentProducts: []
    };
  },
  computed: {
    currentIngredients() {
      if (!this.selectedMeal || !this.selectedMeal.Name) return [];
      return this.mealIngredients[this.selectedMeal.Name] || [];
    }
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
          this.loadIngredientsFromLocalStorage();
          this.loadProductCacheFromLocalStorage();
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
      this.ingredientsFetchAttempted = this.mealIngredients[meal.Name] !== undefined;
      this.activeIngredient = null; // Reset active ingredient when changing meals
    },
    
    formatDate(dateString) {
      if (!dateString) return '';
      const date = new Date(dateString);
      const options = { weekday: 'short', month: 'short', day: 'numeric' };
      return date.toLocaleDateString(undefined, options);
    },
    
    async fetchIngredients() {
      if (!this.selectedMeal || !this.selectedMeal.Name) return;
      
      const mealName = this.selectedMeal.Name;
      this.ingredientsLoading = true;
      this.ingredientsFetchAttempted = true;
      
      try {
        const response = await axios.get(`/api/meal/${encodeURIComponent(mealName)}/ingredients`);
        if (response.data && response.data.status === 'success') {
          // Store ingredients for this meal
          this.mealIngredients = {
            ...this.mealIngredients,
            [mealName]: response.data.ingredients
          };
          
          // Save to localStorage for persistence
          this.saveIngredientsToLocalStorage();
        }
      } catch (error) {
        console.error('Error fetching ingredients:', error);
        // Set empty array for this meal to indicate we tried to fetch
        this.mealIngredients[mealName] = [];
      } finally {
        this.ingredientsLoading = false;
      }
    },
    
    loadIngredientsFromLocalStorage() {
      try {
        const savedIngredients = localStorage.getItem('mealIngredients');
        if (savedIngredients) {
          this.mealIngredients = JSON.parse(savedIngredients);
        }
      } catch (error) {
        console.error('Error loading ingredients from localStorage:', error);
      }
    },
    
    saveIngredientsToLocalStorage() {
      try {
        localStorage.setItem('mealIngredients', JSON.stringify(this.mealIngredients));
      } catch (error) {
        console.error('Error saving ingredients to localStorage:', error);
      }
    },
    
    loadProductCacheFromLocalStorage() {
      try {
        const savedProductCache = localStorage.getItem('productCache');
        if (savedProductCache) {
          this.productCache = JSON.parse(savedProductCache);
        }
      } catch (error) {
        console.error('Error loading product cache from localStorage:', error);
      }
    },
    
    saveProductCacheToLocalStorage() {
      try {
        localStorage.setItem('productCache', JSON.stringify(this.productCache));
      } catch (error) {
        console.error('Error saving product cache to localStorage:', error);
      }
    },
    
    async toggleProductSuggestions(ingredient) {
      // If this ingredient is already active, close it
      if (this.activeIngredient === ingredient) {
        this.activeIngredient = null;
        this.currentProducts = [];
        return;
      }
      
      // Set active ingredient and reset current products
      this.activeIngredient = ingredient;
      this.currentProducts = [];
      
      // Check cache first
      if (this.productCache[ingredient]) {
        this.currentProducts = this.productCache[ingredient];
        return;
      }
      
      // Fetch products for this ingredient
      this.productLoading = true;
      try {
        const response = await axios.get(`/api/ingredients/${encodeURIComponent(ingredient)}/products`);
        if (response.data && response.data.status === 'success') {
          this.currentProducts = response.data.products;
          
          // Cache the products
          this.productCache = {
            ...this.productCache,
            [ingredient]: response.data.products
          };
          
          // Save to localStorage for persistence
          this.saveProductCacheToLocalStorage();
        }
      } catch (error) {
        console.error('Error fetching product suggestions:', error);
        this.currentProducts = [];
      } finally {
        this.productLoading = false;
      }
    },
    
    formatPrice(price) {
      return (price / 100).toFixed(2);
    },
    
    openProductUrl(url) {
      window.open(url, '_blank');
    },

    async reloadIngredients() {
      if (!this.selectedMeal || !this.selectedMeal.Name) return;
      
      const mealName = this.selectedMeal.Name;
      this.ingredientsLoading = true;
      
      try {
        // Use the regenerate-ingredients endpoint to force AI to generate fresh ingredients
        const response = await axios.get(`/api/meal/${encodeURIComponent(mealName)}/regenerate-ingredients`);
        if (response.data && response.data.status === 'success') {
          // Store ingredients for this meal
          this.mealIngredients = {
            ...this.mealIngredients,
            [mealName]: response.data.ingredients
          };
          
          // Save to localStorage for persistence
          this.saveIngredientsToLocalStorage();
        }
      } catch (error) {
        console.error('Error regenerating ingredients:', error);
        // Set empty array for this meal to indicate we tried to fetch
        this.mealIngredients[mealName] = [];
      } finally {
        this.ingredientsLoading = false;
      }
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
  margin-bottom: 1rem;
  color: #495057;
}

.ingredients-list {
  list-style-type: none;
  padding: 0;
  margin: 0;
}

.ingredients-list li {
  margin-bottom: 8px;
  border-radius: 4px;
  background-color: #f8f9fa;
  color: #495057;
  font-size: 0.95rem;
  border-left: 3px solid #90caf9;
  cursor: pointer;
  overflow: hidden;
}

.ingredients-list li.active {
  border-left-color: #1976d2;
  background-color: #e3f2fd;
}

.ingredient-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
}

.chevron {
  border-style: solid;
  border-width: 0.15em 0.15em 0 0;
  content: '';
  display: inline-block;
  height: 0.5em;
  width: 0.5em;
  position: relative;
  vertical-align: middle;
  margin-left: 0.5em;
}

.chevron.down {
  transform: rotate(135deg);
  top: -0.15em;
}

.chevron.up {
  transform: rotate(-45deg);
  top: 0.15em;
}

/* Product suggestions styling */
.product-suggestions {
  padding: 10px 15px;
  background-color: #fff;
  border-top: 1px solid #e9ecef;
}

.loading-products {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem 0;
  color: #6c757d;
}

.loading-spinner.small {
  width: 20px;
  height: 20px;
  margin-right: 10px;
}

.no-products {
  color: #6c757d;
  text-align: center;
  padding: 1rem 0;
  font-style: italic;
}

.products-container {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 10px;
  margin-top: 10px;
}

.product-card {
  border: 1px solid #e9ecef;
  border-radius: 4px;
  overflow: hidden;
  transition: all 0.2s;
}

.product-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.product-image {
  height: 100px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f8f9fa;
  overflow: hidden;
}

.product-image img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.no-image {
  color: #adb5bd;
  font-size: 0.8rem;
  text-align: center;
}

.product-info {
  padding: 8px;
}

.product-name {
  font-size: 0.8rem;
  font-weight: 500;
  color: #212529;
  margin-bottom: 5px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  height: 2.4em;
}

.product-price {
  font-size: 0.8rem;
  font-weight: 600;
  color: #212529;
  display: flex;
  flex-direction: column;
}

.unit-price {
  font-size: 0.7rem;
  color: #6c757d;
  font-weight: normal;
}

.bonus-label {
  display: inline-block;
  background-color: #d32f2f;
  color: white;
  font-size: 0.7rem;
  font-weight: bold;
  padding: 2px 6px;
  border-radius: 2px;
  margin-top: 5px;
}

/* Loading spinner and states */
.ingredients-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem 0;
}

.loading-spinner {
  border: 3px solid #f3f3f3;
  border-top: 3px solid #3498db;
  border-radius: 50%;
  width: 30px;
  height: 30px;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.btn-fetch-ingredients,
.btn-retry {
  background-color: #3498db;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 8px 16px;
  font-size: 0.9rem;
  cursor: pointer;
  transition: background-color 0.2s;
  margin-top: 10px;
}

.btn-fetch-ingredients:hover,
.btn-retry:hover {
  background-color: #2980b9;
}

.click-to-fetch,
.no-ingredients {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1.5rem 0;
  text-align: center;
}

.no-ingredients p {
  color: #6c757d;
  margin-bottom: 1rem;
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
  
  .products-container {
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  }
}

.btn-reload-ingredients {
  background-color: #3498db;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 8px 16px;
  font-size: 0.9rem;
  cursor: pointer;
  transition: background-color 0.2s;
  margin-left: 10px;
}

.btn-reload-ingredients:disabled {
  background-color: #b0c4de;
  cursor: not-allowed;
}

.btn-reload-ingredients:hover:not(:disabled) {
  background-color: #2980b9;
}

.ingredients-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>