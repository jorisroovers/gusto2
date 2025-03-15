`<template>
  <div class="recipe-list">
    <div class="recipe-controls">
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
      <div v-for="recipe in recipes" :key="recipe.Name" class="recipe-card">
        <h3>{{ recipe.Name }}</h3>
        <div class="tags" v-if="recipe.Tags">
          <span v-for="tag in recipe.Tags.split(',')" 
                :key="tag.trim()" 
                class="tag"
          >
            {{ tag.trim() }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'RecipeList',
  data() {
    return {
      recipes: [],
      loading: true,
      error: null,
      notification: '',
      notificationType: 'info'
    };
  },
  methods: {
    async loadRecipes() {
      this.loading = true;
      this.error = null;
      try {
        const response = await axios.get('/api/recipes');
        this.recipes = response.data.recipes;
      } catch (error) {
        console.error('Error loading recipes:', error);
        this.error = 'Failed to load recipes';
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
        this.showNotification('Recipes populated from meal plan', 'success');
      } catch (error) {
        console.error('Error populating recipes:', error);
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
    }
  },
  mounted() {
    this.loadRecipes();
  }
};
</script>

<style scoped>
.recipe-list {
  padding: 20px;
}

.recipe-controls {
  margin-bottom: 20px;
  display: flex;
  justify-content: center;
}

.populate-button {
  background-color: #3498db;
  border: none;
  color: white;
  padding: 10px 20px;
  text-align: center;
  text-decoration: none;
  display: inline-block;
  font-size: 14px;
  cursor: pointer;
  border-radius: 4px;
  transition: background-color 0.3s;
}

.populate-button:hover {
  background-color: #2980b9;
}

.populate-button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.notification {
  padding: 10px;
  margin-bottom: 15px;
  border-radius: 5px;
  font-weight: 500;
  text-align: center;
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

.recipes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 20px;
  margin-top: 20px;
}

.recipe-card {
  background: white;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.recipe-card h3 {
  margin: 0 0 10px 0;
  color: #2c3e50;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.tag {
  background-color: #e9ecef;
  color: #495057;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.loading, .error, .no-recipes {
  text-align: center;
  padding: 20px;
  color: #666;
}

.error {
  color: #dc3545;
}
</style>
`