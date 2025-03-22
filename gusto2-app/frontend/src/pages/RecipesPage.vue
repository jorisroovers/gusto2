<template>
  <div class="recipes-page">
    <div class="content-wrapper">
      <div class="recipes-layout">
        <div class="main-content">
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
              v-for="tag in availableTags" 
              :key="tag"
              :class="['filter-tag', { active: selectedTags.includes(tag) }]"
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
      meals: []
    };
  },
  computed: {
    filteredMeals() {
      if (!this.selectedTags.length) return [];
      
      return this.meals.filter(meal => {
        if (!meal.Tags) return false;
        const mealTags = meal.Tags.split(',').map(t => t.trim());
        return this.selectedTags.every(tag => mealTags.includes(tag));
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
  background-color: #f0f2f5;
  color: #2c3e50;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 500;
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
  background-color: #f0f2f5;
  color: #2c3e50;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.filter-tag:hover {
  background-color: #e4e7eb;
}

.filter-tag.active {
  background-color: #3498db;
  color: white;
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