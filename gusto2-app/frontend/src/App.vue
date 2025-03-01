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
            <button 
              @click="previousMeal" 
              :disabled="currentIndex <= 0"
              class="nav-button"
            >
              &lt; Previous
            </button>
            <div class="meal-info">
              <h3>{{ currentMeal.Name }}</h3>
              <p v-if="currentMeal.Date">Date: {{ formatDate(currentMeal.Date) }}</p>
              <p v-if="currentMeal.Description">{{ currentMeal.Description }}</p>
              <p class="meal-counter">Meal {{ currentIndex + 1 }} of {{ meals.length }}</p>
            </div>
            <button 
              @click="nextMeal" 
              :disabled="currentIndex >= meals.length - 1"
              class="nav-button"
            >
              Next &gt;
            </button>
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
  align-items: center;
  justify-content: space-between;
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
  margin: 5px;
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

.loading, .error, .no-meals {
  padding: 20px;
  text-align: center;
}

.error {
  color: #e74c3c;
}
</style>
