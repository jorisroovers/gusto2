<template>
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
      <div v-for="recipe in filteredRecipes" :key="recipe.Name" class="recipe-card">
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
  expose: ['populateFromMeals'],
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
      notificationType: 'info'
    };
  },
  computed: {
    filteredRecipes() {
      if (!this.selectedTags.length) return this.recipes;
      
      return this.recipes.filter(recipe => {
        if (!recipe.Tags) return false;
        const recipeTags = recipe.Tags.split(',').map(t => t.trim());
        return this.selectedTags.every(tag => recipeTags.includes(tag));
      });
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
    async loadRecipes() {
      this.loading = true;
      this.error = null;
      try {
        const response = await axios.get('/api/recipes');
        this.recipes = response.data.recipes;
        this.$parent.updateAvailableTags(this.allTags);
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
        this.$parent.updateAvailableTags(this.allTags);
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
  width: 100%;
}

.recipe-controls {
  margin-bottom: 1.5rem;
  display: flex;
  justify-content: center;
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
}

.recipe-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
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
  background-color: #f0f2f5;
  color: #2c3e50;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 500;
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

@media (max-width: 768px) {
  .recipes-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }
}
</style>