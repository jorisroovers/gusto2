<template>
  <div id="app">
    <header>
      <h1>Gusto2 App</h1>
    </header>
    <main>
      <div class="card">
        <div v-if="loading" class="loading">Loading meals...</div>
        <div v-else-if="error" class="error">{{ error }}</div>
        <div v-else-if="meals.length === 0" class="no-meals">No meals found</div>
        <div v-else class="meal-display">
          <div class="navigation">
            <div class="nav-column">
              <button 
                @click="previousMeal" 
                :disabled="currentIndex <= 0"
                class="nav-button"
              >
                &lt; Previous
              </button>
              <button 
                @click="findPreviousUnplanned" 
                class="unplanned-button"
              >
                &lt; Previous Unplanned
              </button>
            </div>
            
            <div class="meal-info">
              <h3>{{ currentMeal.Name }}</h3>
              <p v-if="currentMeal.Date">Date: {{ formatDate(currentMeal.Date) }}</p>
              <p v-if="currentMeal.Description">{{ currentMeal.Description }}</p>
              <p class="meal-counter">Meal {{ currentIndex + 1 }} of {{ meals.length }}</p>
              <div class="button-group">
                <button @click="selectTodaysMeal" class="today-button">Today</button>
              </div>
            </div>
            
            <div class="nav-column">
              <button 
                @click="nextMeal" 
                :disabled="currentIndex >= meals.length - 1"
                class="nav-button"
              >
                Next &gt;
              </button>
              <button 
                @click="findNextUnplanned" 
                class="unplanned-button"
              >
                Next Unplanned &gt;
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'App',
  data() {
    return {
      meals: [],
      currentIndex: 0,
      loading: true,
      error: null,
      message: 'Loading meals from backend...'
    };
  },
  computed: {
    currentMeal() {
      return this.meals.length > 0 ? this.meals[this.currentIndex] : {};
    }
  },
  methods: {
    async fetchMeals() {
      this.loading = true;
      this.error = null;
      try {
        const response = await axios.get('/api/hello');
        if (response.data && response.data.meals && response.data.meals.length > 0) {
          this.meals = response.data.meals;
          this.selectTodaysMeal();
        } else {
          this.error = 'No meals data found';
        }
      } catch (error) {
        console.error('Error fetching meals:', error);
        this.error = 'Error fetching meals from backend';
      } finally {
        this.loading = false;
      }
    },
    selectTodaysMeal() {
      if (!this.meals.length) return;
      
      // Get today's date without time information
      const today = new Date();
      const todayYear = today.getFullYear();
      const todayMonth = today.getMonth();
      const todayDay = today.getDate();
      
      // Find index of meal with today's date
      const todayIndex = this.meals.findIndex(meal => {
        if (!meal.Date) return false;
        
        const mealDate = new Date(meal.Date);
        return (
          mealDate.getFullYear() === todayYear &&
          mealDate.getMonth() === todayMonth &&
          mealDate.getDate() === todayDay
        );
      });
      
      // If found, set the current index to today's meal
      if (todayIndex !== -1) {
        this.currentIndex = todayIndex;
        console.log(`Found today's meal at index ${todayIndex}`);
      } else {
        console.log('No meal found for today, finding nearest meal');
        // Find nearest future meal as fallback
        this.findNearestMeal();
      }
    },
    findNearestMeal() {
      if (!this.meals.length) return;
      
      // Create today date at midnight for proper comparison
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      
      let closestIndex = 0;
      let smallestDiff = Infinity;
      let preferFutureMeals = true; // Prefer future meals over past ones
      
      // First try to find the nearest future meal
      this.meals.forEach((meal, index) => {
        if (!meal.Date) return;
        
        const mealDate = new Date(meal.Date);
        mealDate.setHours(0, 0, 0, 0);
        
        // Calculate difference in days
        const diff = mealDate - today;
        
        // If we're looking for future meals, only consider those
        if (preferFutureMeals && diff >= 0) {
          if (diff < smallestDiff) {
            smallestDiff = diff;
            closestIndex = index;
          }
        }
      });
      
      // If no future meals found, find the closest past meal
      if (smallestDiff === Infinity) {
        smallestDiff = Infinity;
        this.meals.forEach((meal, index) => {
          if (!meal.Date) return;
          
          const mealDate = new Date(meal.Date);
          mealDate.setHours(0, 0, 0, 0);
          
          // Use absolute difference for past meals
          const diff = Math.abs(mealDate - today);
          
          if (diff < smallestDiff) {
            smallestDiff = diff;
            closestIndex = index;
          }
        });
      }
      
      this.currentIndex = closestIndex;
    },
    nextMeal() {
      if (this.currentIndex < this.meals.length - 1) {
        this.currentIndex++;
      }
    },
    previousMeal() {
      if (this.currentIndex > 0) {
        this.currentIndex--;
      }
    },
    findNextUnplanned() {
      if (!this.meals.length) return;
      
      // Get the date of the current meal
      const currentDate = this.currentMeal.Date ? new Date(this.currentMeal.Date) : new Date();
      currentDate.setHours(0, 0, 0, 0);
      
      // Find the next meal with an empty name (unplanned)
      const nextUnplannedIndex = this.meals.findIndex((meal, index) => {
        // Only check meals after the current one
        if (index <= this.currentIndex) return false;
        
        // Check if meal has a date but no name (or empty name)
        return meal.Date && (!meal.Name || meal.Name.trim() === '');
      });
      
      if (nextUnplannedIndex !== -1) {
        console.log(`Found next unplanned meal at index ${nextUnplannedIndex}`);
        this.currentIndex = nextUnplannedIndex;
      } else {
        console.log('No unplanned meals found in the future');
      }
    },
    
    findPreviousUnplanned() {
      if (!this.meals.length) return;
      
      // Find the previous meal with an empty name (unplanned)
      // We need to loop backwards from the current index
      let prevUnplannedIndex = -1;
      
      for (let i = this.currentIndex - 1; i >= 0; i--) {
        const meal = this.meals[i];
        // Check if meal has a date but no name (or empty name)
        if (meal.Date && (!meal.Name || meal.Name.trim() === '')) {
          prevUnplannedIndex = i;
          break;
        }
      }
      
      if (prevUnplannedIndex !== -1) {
        console.log(`Found previous unplanned meal at index ${prevUnplannedIndex}`);
        this.currentIndex = prevUnplannedIndex;
      } else {
        console.log('No unplanned meals found in the past');
      }
    },
    formatDate(dateString) {
      if (!dateString) return '';
      const date = new Date(dateString);
      return date.toLocaleDateString();
    }
  },
  mounted() {
    // Fetch meals when the component is mounted
    this.fetchMeals();
  }
};
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  margin-top: 60px;
}

header {
  margin-bottom: 30px;
}

.card {
  max-width: 600px;
  margin: 0 auto;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
  background-color: #f9f9f9;
}

.navigation {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.nav-column {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.meal-info {
  flex: 1;
  margin: 0 20px;
}

.meal-counter {
  font-size: 0.8em;
  color: #666;
  margin-top: 10px;
}

.nav-button {
  background-color: #4CAF50;
  border: none;
  color: white;
  padding: 10px 15px;
  text-align: center;
  text-decoration: none;
  display: inline-block;
  font-size: 14px;
  cursor: pointer;
  border-radius: 4px;
  transition: background-color 0.3s;
  min-width: 100px;
}

.nav-button:hover {
  background-color: #45a049;
}

.nav-button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.button-group {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
  margin-top: 10px;
}

.today-button {
  background-color: #3498db;
  border: none;
  color: white;
  padding: 8px 12px;
  text-align: center;
  text-decoration: none;
  display: inline-block;
  font-size: 14px;
  cursor: pointer;
  border-radius: 4px;
  transition: background-color 0.3s;
}

.today-button:hover {
  background-color: #2980b9;
}

.unplanned-button {
  background-color: #9b59b6;
  border: none;
  color: white;
  padding: 8px 12px;
  text-align: center;
  text-decoration: none;
  display: inline-block;
  font-size: 13px;
  cursor: pointer;
  border-radius: 4px;
  transition: background-color 0.3s;
  min-width: 100px;
}

.unplanned-button:hover {
  background-color: #8e44ad;
}

.loading, .error, .no-meals {
  padding: 20px;
  text-align: center;
}

.error {
  color: #e74c3c;
}
</style>
