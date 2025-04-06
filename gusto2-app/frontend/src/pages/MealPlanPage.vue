<template>
  <div class="meal-plan-page">
    <div class="header-buttons">
      <button 
        @click="saveAllChanges" 
        class="save-all-button" 
        :disabled="!hasChanges || loading"
        :title="!hasChanges ? 'No changes to save' : 'Save all changes'"
      >
        Save All Changes ({{ changedIndices.length }})
      </button>
      <button 
        @click="reloadMeals" 
        class="reload-button" 
        :disabled="loading"
        title="Reload meals from server (discards unsaved changes)"
      >
        Reload
      </button>
    </div>

    <div class="content-wrapper">
      <!-- Notification area for saving/reloading status -->
      <div v-if="notification" class="notification" :class="notificationType">
        {{ notification }}
      </div>

      <div class="main-content">
        <div v-if="loading" class="loading">Loading meals...</div>
        <div v-else-if="error" class="error">{{ error }}</div>
        <div v-else-if="meals.length === 0" class="no-meals">No meals found</div>
        <div v-else class="meal-display">
          <!-- Day view content -->
          <div class="meal-browser">
            <!-- Navigation controls at the top -->
            <div class="meal-navigation">
              <div class="nav-header">
                <button 
                  @click="previousMeal" 
                  :disabled="currentIndex <= 0 || editMode"
                  class="nav-button"
                >
                  <span class="nav-icon">←</span>
                  <span class="nav-text">Previous</span>
                </button>
                
                <div class="meal-date-container">
                  <p v-if="currentMeal.Date" class="date-display">{{ formatDate(currentMeal.Date) }}</p>
                  <span v-if="isCurrentMealChanged" class="changed-indicator" title="This meal has unsaved changes">*</span>
                  <button @click="selectTodaysMeal" class="today-button" :disabled="editMode">Today</button>
                </div>

                <button 
                  @click="nextMeal" 
                  :disabled="currentIndex >= meals.length - 1 || editMode"
                  class="nav-button"
                >
                  <span class="nav-text">Next</span>
                  <span class="nav-icon">→</span>
                </button>
              </div>

              <div class="navigation-actions">
                <div class="meal-counter">{{ currentIndex + 1 }} of {{ meals.length }}</div>

                <div class="special-nav-buttons">
                  <button 
                    @click="findPreviousUnplanned" 
                    class="unplanned-button"
                    :disabled="editMode"
                    title="Find previous day without a planned meal"
                  >
                    <span class="nav-icon">←</span> Previous Unplanned
                  </button>
                  <button 
                    @click="findNextUnplanned" 
                    class="unplanned-button"
                    :disabled="editMode"
                    title="Find next day without a planned meal"
                  >
                    Next Unplanned <span class="nav-icon">→</span>
                  </button>
                </div>
              </div>
            </div>

            <!-- Meal information card -->
            <div class="meal-card">
              <div v-if="!editMode" class="meal-card-view">
                <div class="meal-card-header">
                  <div v-if="currentMeal.Name" class="meal-title">
                    <h3>{{ currentMeal.Name }}</h3>
                  </div>
                  <div v-else class="meal-title no-meal">
                    <h3>No meal planned</h3>
                  </div>

                  <div class="meal-actions">
                    <button v-if="!editMode" @click="startEdit" class="edit-button" title="Edit this meal">
                      <span class="edit-icon">✎</span>
                      <span class="edit-text">Edit</span>
                    </button>
                    
                    <div class="action-buttons">
                      <button v-if="!showUndoConfirmation" @click="showUndoConfirmation = true" class="undo-button" title="Reload from Notion">↺</button>
                      <div v-else class="undo-confirmation">
                        <span>Reload from Notion?</span>
                        <button @click="confirmUndo" class="confirm-yes">Yes</button>
                        <button @click="showUndoConfirmation = false" class="confirm-no">No</button>
                      </div>
                      
                      <button v-if="currentMeal.Name && !showDeleteConfirmation" 
                        @click="showDeleteConfirmation = true" 
                        class="delete-button" 
                        title="Remove meal">×</button>
                      <div v-if="showDeleteConfirmation" class="delete-confirmation">
                        <span>Delete?</span>
                        <button @click="confirmDelete" class="confirm-yes">Yes</button>
                        <button @click="showDeleteConfirmation = false" class="confirm-no">No</button>
                      </div>
                    </div>
                  </div>
                </div>
                
                <!-- Add loading spinner when a specific meal is being reloaded -->
                <div v-if="currentMeal.isLoading" class="meal-loading-spinner">
                  <div class="spinner"></div>
                  <p>Reloading meal from Notion...</p>
                </div>
                
                <!-- Add tags display -->
                <div v-else-if="currentMeal.Tags" class="meal-tags">
                  <div class="tags-container">
                    <span v-for="tag in currentMeal.Tags.split(',')" 
                          :key="tag.trim()" 
                          class="tag"
                          :data-tag="tag.trim().toLowerCase()"
                    >
                      {{ tag.trim() }}
                    </span>
                  </div>
                </div>

                <div class="meal-card-body">
                  <div v-if="currentMeal.Notes" class="meal-description">
                    <p>{{ currentMeal.Notes }}</p>
                  </div>
                  <div v-else class="meal-description empty">
                    <p>No notes</p>
                  </div>
                </div>
              </div>

              <div v-else class="edit-form">
                <div class="form-group">
                  <label for="mealName">Meal Name:</label>
                  <recipe-autocomplete 
                    v-model="editedMeal.Name" 
                    placeholder="Search for a recipe..."
                    @recipe-selected="onRecipeSelected"
                  />
                </div>
                <div class="form-group">
                  <label for="mealDescription">Description/Notes:</label>
                  <textarea 
                    id="mealDescription" 
                    v-model="editedMeal.Notes" 
                    placeholder="Enter notes or description"
                    rows="2"
                  ></textarea>
                </div>
                <div class="form-group">
                  <label for="mealTags">Tags:</label>
                  <tag-input 
                    v-model="editedMeal.Tags"
                    :suggestions="tagSuggestions"
                  />
                </div>
                
                <div class="edit-actions">
                  <button @click="saveMeal" class="save-button">Save</button>
                  <button @click="cancelEdit" class="cancel-button">Cancel</button>
                </div>
              </div>
            </div>

            <!-- Meal suggestions section -->
            <div class="meal-suggestions">
              <div class="suggestion-actions">
                <button @click="suggestMeal" class="suggest-button" :disabled="loading">
                  {{ suggestedMeal ? 'Suggest Another Meal' : 'Suggest Meal' }}
                </button>
                <div v-if="suggestedMeal" class="suggested-recipe">
                  <div class="suggested-meal-info">
                    <h4>Suggested:</h4>
                    <p>{{ suggestedMeal.Name }}</p>
                    <div v-if="suggestedMeal.Tags" class="suggested-tags">
                      <span v-for="tag in suggestedMeal.Tags.split(',')" 
                            :key="tag.trim()" 
                            class="suggested-tag"
                            :data-tag="tag.trim().toLowerCase()"
                      >
                        {{ tag.trim() }}
                      </span>
                    </div>
                  </div>
                  <button @click="acceptSuggestion" class="accept-button">Accept</button>
                </div>
              </div>
            </div>
            
            <!-- Meal Plan Rules Component -->
            <meal-plan-rules
              :current-date="currentMeal.Date"
              :current-index="currentIndex"
              @use-suggestion="handleRuleSuggestion"
              class="meal-rules-section"
            />
          </div>

          <!-- Calendar picker - this stays the same as requested -->
          <div class="calendar-container">
            <calendar-picker 
              v-if="!loading && !error" 
              :meals="meals" 
              :selected-date="currentMeal.Date"
              :changed-indices="changedIndices"
              @date-selected="selectDate"
              class="calendar-section"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import CalendarPicker from '../components/CalendarPicker.vue';
import MealPlanRules from '../components/MealPlanRules.vue';
import TagInput from '../components/TagInput.vue';
import RecipeAutocomplete from '../components/RecipeAutocomplete.vue';

export default {
  name: 'MealPlanPage',
  components: {
    CalendarPicker,
    MealPlanRules,
    TagInput,
    RecipeAutocomplete
  },
  data() {
    return {
      meals: [],
      currentIndex: 0,
      loading: true,
      error: null,
      message: 'Loading meals from backend...',
      editMode: false,
      editedMeal: {},
      notification: '',
      notificationType: 'info',
      hasChanges: false,
      changedIndices: [],
      lastViewedDate: null,
      suggestedMeal: null,
      showDeleteConfirmation: false,
      showUndoConfirmation: false,
      tagSuggestions: []
    };
  },
  computed: {
    currentMeal() {
      return this.meals.length > 0 ? this.meals[this.currentIndex] : {};
    },
    isCurrentMealChanged() {
      return this.changedIndices.includes(this.currentIndex);
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
          
          // Get changed indices from separate endpoint
          try {
            const changesResponse = await axios.get('/api/meals/changes');
            if (changesResponse.data && changesResponse.data.changedIndices) {
              this.changedIndices = changesResponse.data.changedIndices;
              this.hasChanges = this.changedIndices.length > 0;
            }
          } catch (changesError) {
            this.changedIndices = [];
            this.hasChanges = false;
          }
          
          this.selectTodaysMeal();
        } else {
          this.error = 'No meals data found';
        }
      } catch (error) {
        this.error = 'Error fetching meals from backend';
      } finally {
        this.loading = false;
      }
    },
    
    async saveAllChanges() {
      if (!this.hasChanges) return;
      
      this.loading = true;
      try {
        const response = await axios.post('/api/meals/save', this.meals);
        
        if (response.data && response.data.status === 'success') {
          this.hasChanges = false;
          this.changedIndices = [];
          
          const notionMsg = response.data.notionUpdated ? ' and synchronized with Notion' : '';
          this.showNotification(`All changes saved successfully${notionMsg}!`, 'success');
        } else {
          throw new Error('Unexpected response from server');
        }
      } catch (error) {
        this.showNotification('Failed to save changes: ' + (error.response?.data?.detail || error.message), 'error');
      } finally {
        this.loading = false;
      }
    },
    
    async reloadMeals() {
      this.loading = true;
      
      const currentDate = this.currentMeal.Date ? new Date(this.currentMeal.Date) : null;
      this.lastViewedDate = currentDate;
      
      try {
        const response = await axios.get('/api/meals/reload');
        if (response.data && response.data.meals) {
          this.meals = response.data.meals;
          
          this.hasChanges = false;
          this.changedIndices = [];
          
          this.restoreMealPosition();
          
          this.showNotification('Meals reloaded from server', 'info');
        }
      } catch (error) {
        this.showNotification('Failed to reload meals: ' + (error.response?.data?.detail || error.message), 'error');
      } finally {
        this.loading = false;
      }
    },
    
    restoreMealPosition() {
      if (!this.lastViewedDate || !this.meals.length) {
        this.selectTodaysMeal();
        return;
      }
      
      const lastViewedIndex = this.meals.findIndex(meal => {
        if (!meal.Date) return false;
        
        const mealDate = new Date(meal.Date);
        return (
          mealDate.getFullYear() === this.lastViewedDate.getFullYear() &&
          mealDate.getMonth() === this.lastViewedDate.getMonth() &&
          mealDate.getDate() === this.lastViewedDate.getDate()
        );
      });
      
      if (lastViewedIndex !== -1) {
        this.currentIndex = lastViewedIndex;
      } else {
        this.findNearestDateTo(this.lastViewedDate);
      }
    },
    
    findNearestDateTo(targetDate) {
      if (!this.meals.length || !targetDate) return;
      
      let closestIndex = 0;
      let smallestDiff = Infinity;
      
      this.meals.forEach((meal, index) => {
        if (!meal.Date) return;
        
        const mealDate = new Date(meal.Date);
        mealDate.setHours(0, 0, 0, 0);
        
        const diff = Math.abs(mealDate - targetDate);
        
        if (diff < smallestDiff) {
          smallestDiff = diff;
          closestIndex = index;
        }
      });
      
      this.currentIndex = closestIndex;
    },
    
    showNotification(message, type = 'info') {
      this.notification = message;
      this.notificationType = type;
      
      setTimeout(() => {
        this.notification = '';
      }, 3000);
    },
    
    startEdit() {
      this.editedMeal = { ...this.currentMeal };
      this.editMode = true;
    },
    
    cancelEdit() {
      this.editMode = false;
      this.editedMeal = {};
    },
    
    async saveMeal() {
      this.loading = true;
      try {
        // Convert tags to lowercase before saving
        const mealData = {
          ...this.editedMeal,
          Tags: this.editedMeal.Tags ? this.editedMeal.Tags.split(',').map(t => t.trim().toLowerCase()).join(',') : ''
        };
        
        const response = await axios.put(`/api/meal/${this.currentIndex}`, mealData);
        
        this.meals[this.currentIndex] = { ...mealData };
        
        this.hasChanges = true;
        this.changedIndices = response.data.changedIndices || [];
        
        this.showNotification('Meal updated! Use Save All to persist to disk.', 'success');
        
        this.editMode = false;
        this.editedMeal = {};
      } catch (error) {
        this.showNotification('Failed to update meal', 'error');
      } finally {
        this.loading = false;
      }
    },
    
    selectTodaysMeal() {
      if (!this.meals.length) return;
      
      const today = new Date();
      const todayYear = today.getFullYear();
      const todayMonth = today.getMonth();
      const todayDay = today.getDate();
      
      const todayIndex = this.meals.findIndex(meal => {
        if (!meal.Date) return false;
        
        const mealDate = new Date(meal.Date);
        return (
          mealDate.getFullYear() === todayYear &&
          mealDate.getMonth() === todayMonth &&
          mealDate.getDate() === todayDay
        );
      });
      
      if (todayIndex !== -1) {
        this.currentIndex = todayIndex;
      } else {
        this.findNearestMeal();
      }
    },
    
    findNearestMeal() {
      if (!this.meals.length) return;
      
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      
      let closestIndex = 0;
      let smallestDiff = Infinity;
      let preferFutureMeals = true;
      
      this.meals.forEach((meal, index) => {
        if (!meal.Date) return;
        
        const mealDate = new Date(meal.Date);
        mealDate.setHours(0, 0, 0, 0);
        
        const diff = mealDate - today;
        
        if (preferFutureMeals && diff >= 0) {
          if (diff < smallestDiff) {
            smallestDiff = diff;
            closestIndex = index;
          }
        }
      });
      
      if (smallestDiff === Infinity) {
        smallestDiff = Infinity;
        this.meals.forEach((meal, index) => {
          if (!meal.Date) return;
          
          const mealDate = new Date(meal.Date);
          mealDate.setHours(0, 0, 0, 0);
          
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
      
      const nextUnplannedIndex = this.meals.findIndex((meal, index) => {
        if (index <= this.currentIndex) return false;
        return meal.Date && (!meal.Name || meal.Name.trim() === '');
      });
      
      if (nextUnplannedIndex !== -1) {
        this.currentIndex = nextUnplannedIndex;
      }
    },
    
    findPreviousUnplanned() {
      if (!this.meals.length) return;
      
      let prevUnplannedIndex = -1;
      
      for (let i = this.currentIndex - 1; i >= 0; i--) {
        const meal = this.meals[i];
        if (meal.Date && (!meal.Name || meal.Name.trim() === '')) {
          prevUnplannedIndex = i;
          break;
        }
      }
      
      if (prevUnplannedIndex !== -1) {
        this.currentIndex = prevUnplannedIndex;
      }
    },
    
    formatDate(dateString) {
      if (!dateString) return '';
      const date = new Date(dateString);
      return date.toLocaleDateString();
    },
    
    selectDate(dateString) {
      const selectedIndex = this.meals.findIndex(meal => meal.Date === dateString);
      if (selectedIndex !== -1) {
        this.currentIndex = selectedIndex;
      }
    },
    
    async suggestMeal() {
      try {
        const recipesResponse = await axios.get('/api/recipes');
        const recipes = recipesResponse.data.recipes;
        
        if (!recipes || recipes.length === 0) {
          this.showNotification('No recipes available to suggest', 'error');
          return;
        }

        // Filter out the current suggestion if we have one
        const availableRecipes = recipes.filter(r => 
          !this.suggestedMeal || r.Name !== this.suggestedMeal.Name
        );

        if (availableRecipes.length === 0) {
          // If we've shown all recipes, reset and use the full list
          this.suggestedMeal = recipes[Math.floor(Math.random() * recipes.length)];
        } else {
          // Pick a random recipe from the available ones
          this.suggestedMeal = availableRecipes[Math.floor(Math.random() * availableRecipes.length)];
        }
      } catch (error) {
        this.showNotification('Failed to fetch recipes for suggestion', 'error');
      }
    },

    async acceptSuggestion() {
      if (!this.suggestedMeal) return;

      const meal = {
        Name: this.suggestedMeal.Name,
        Tags: this.suggestedMeal.Tags || ''
      };

      try {
        const response = await axios.put(`/api/meal/${this.currentIndex}`, meal);
        
        if (response.data.status === 'success') {
          this.meals[this.currentIndex] = {
            ...this.meals[this.currentIndex],
            ...meal
          };
          
          this.changedIndices = response.data.changedIndices;
          this.hasChanges = this.changedIndices.length > 0;
          
          this.suggestedMeal = null;
          
          this.showNotification('Recipe added to meal plan!', 'success');
        }
      } catch (error) {
        this.showNotification('Failed to add recipe to meal plan', 'error');
      }
    },

    async confirmDelete() {
      try {
        const response = await axios.put(`/api/meal/${this.currentIndex}`, {
          Name: '',
          Tags: '',
          Notes: ''
        });
        
        if (response.data.status === 'success') {
          this.meals[this.currentIndex] = {
            ...this.meals[this.currentIndex],
            Name: '',
            Tags: '',
            Notes: ''
          };
          
          this.changedIndices = response.data.changedIndices;
          this.hasChanges = this.changedIndices.length > 0;
          
          this.showNotification('Meal removed successfully!', 'success');
        }
      } catch (error) {
        this.showNotification('Failed to remove meal', 'error');
      } finally {
        this.showDeleteConfirmation = false;
      }
    },
    
    // Handle rule-based meal suggestions
    async handleRuleSuggestion({ meal, index }) {
      try {
        // Create the meal data structure expected by the backend
        const mealData = {
          Name: meal.name,
          Tags: meal.tags || ''
        };
        
        const response = await axios.put(`/api/meal/${index}`, mealData);
        
        if (response.data.status === 'success') {
          // Update the local meals array with the full meal structure
          this.meals[index] = {
            ...this.meals[index], // Keep existing fields like Date
            ...mealData
          };
          
          this.changedIndices = response.data.changedIndices;
          this.hasChanges = this.changedIndices.length > 0;
          
          this.showNotification('Rule-suggested meal added to meal plan!', 'success');
        }
      } catch (error) {
        this.showNotification('Failed to add rule-suggested meal to meal plan', 'error');
      }
    },

    async fetchTagSuggestions() {
      try {
        // Get all unique tags from both meals and recipes
        const [mealsResponse, recipesResponse] = await Promise.all([
          axios.get('/api/meals'),
          axios.get('/api/recipes')
        ]);

        const mealTags = mealsResponse.data.meals
          .flatMap(meal => meal.Tags ? meal.Tags.split(',').map(t => t.trim()) : []);
        const recipeTags = recipesResponse.data.recipes
          .flatMap(recipe => recipe.Tags ? recipe.Tags.split(',').map(t => t.trim()) : []);

        // Combine and deduplicate tags
        this.tagSuggestions = [...new Set([...mealTags, ...recipeTags])]
          .filter(tag => tag) // Remove empty tags
          .sort();
      } catch (error) {
        console.error('Error fetching tag suggestions:', error);
      }
    },

    onRecipeSelected(recipe) {
      // When a recipe is selected from autocomplete, also set its tags
      if (recipe && recipe.Tags) {
        this.editedMeal.Tags = recipe.Tags;
      }
    },

    async confirmUndo() {
      // Set loading state only for this specific meal
      const mealIndex = this.currentIndex;
      // Use direct property assignment in Vue 3 instead of $set
      if (!this.meals[mealIndex].isLoading) {
        // Use direct assignment for Vue 3 reactivity
        this.meals[mealIndex] = {
          ...this.meals[mealIndex],
          isLoading: true
        };
      }
      
      try {
        // Step 1: Call the backend to reload this specific meal from Notion
        const response = await axios.get(`/api/meal/${mealIndex}/reload-from-notion`);
        
        if (response.data && response.data.status === 'success') {
          // Step 2: Update just this specific meal with the reloaded data from Notion
          const updatedMeal = response.data.meal;
          
          // Preserve the Date property and update other properties
          this.meals[mealIndex] = {
            ...updatedMeal,
            Date: this.meals[mealIndex].Date // Make sure we keep the original Date
          };
          
          // Step 3: Remove this meal from the changedIndices array in the frontend
          this.changedIndices = this.changedIndices.filter(index => index !== mealIndex);
          this.hasChanges = this.changedIndices.length > 0;
          
          // Step 4: Make a separate call to explicitly persist the removal of this index from changedIndices
          // This ensures the change persists through page refreshes
          try {
            // We need to save all meals to persist the changes to the backend
            await axios.post('/api/meals/save', this.meals);
          } catch (saveError) {
            console.error('Failed to persist undo changes:', saveError);
            // Don't show error to user as the main functionality worked
          }
          
          this.showNotification('Meal reloaded from Notion successfully!', 'success');
        } else {
          throw new Error('Unable to reload meal from Notion');
        }
      } catch (error) {
        this.showNotification('Failed to reload meal from Notion: ' + (error.response?.data?.message || error.message), 'error');
      } finally {
        // Remove the loading state for this specific meal
        if (this.meals[mealIndex]) {
          this.meals[mealIndex] = {
            ...this.meals[mealIndex],
            isLoading: false
          };
        }
        this.showUndoConfirmation = false;
      }
    },
  },
  async mounted() {
    await Promise.all([
      this.fetchMeals(),
      this.fetchTagSuggestions()
    ]);

    // Check if we have a date query parameter
    const dateParam = this.$route.query.date;
    if (dateParam) {
      this.selectDate(dateParam);
    }
  },
  watch: {
    // Watch for route changes to handle navigation between meals
    '$route.query.date'(newDate) {
      if (newDate) {
        this.selectDate(newDate);
      }
    }
  }
};
</script>

<style scoped>
.meal-plan-page {
  width: 100%;
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 1rem;
}

.header-buttons {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  justify-content: center;
}

.header-buttons button {
  width: fit-content;
  min-width: 120px;
  padding: 8px 16px;
  border-radius: 4px;
  border: 1px solid #ddd;
  background-color: white;
  cursor: pointer;
  transition: all 0.3s ease;
}

.header-buttons button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.save-all-button {
  background-color: #4caf50 !important;
  color: white;
  border-color: #45a049 !important;
}

.save-all-button:hover:not(:disabled) {
  background-color: #45a049 !important;
}

.reload-button:hover:not(:disabled) {
  background-color: #f5f5f5;
}

.content-wrapper {
  margin: 0 auto;
}

.main-content {
  width: 100%;
}

.meal-display {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.meal-browser {
  flex: 1;
  min-width: 0; /* Prevent flex items from overflowing */
}

/* Improve loading/error state styling */
.loading, .error, .no-meals {
  text-align: center;
  padding: 2rem;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.loading {
  color: #3498db;
}

.error {
  color: #e74c3c;
}

.no-meals {
  color: #7f8c8d;
}

/* Improve navigation controls */
.meal-navigation {
  width: 100%;
  max-width: 800px;
  margin: 0 auto 20px;
  display: flex;
  flex-direction: column;
  gap: 15px;
  padding: 15px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.nav-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.nav-button {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  transition: all 0.3s ease;
  min-width: 110px;
  justify-content: center;
}

.nav-button:hover:not(:disabled) {
  background-color: #f5f5f5;
  border-color: #bbb;
}

.nav-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.nav-icon {
  font-size: 1.2em;
  line-height: 1;
}

.meal-date-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  position: relative;
  padding: 0 10px;
}

.date-display {
  font-size: 1.2em;
  font-weight: 600;
  color: #2c3e50;
  margin: 0;
}

.changed-indicator {
  position: absolute;
  top: -5px;
  right: -5px;
  color: #e74c3c;
  font-weight: bold;
  font-size: 1.2em;
}

.today-button {
  background-color: #3498db;
  color: white;
  border: none;
  padding: 4px 10px;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
  font-size: 0.85em;
}

.today-button:hover:not(:disabled) {
  background-color: #2980b9;
}

.today-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.navigation-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.meal-counter {
  color: #666;
  font-size: 0.9em;
  text-align: center;
}

.special-nav-buttons {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}

.unplanned-button {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 0.85em;
}

.unplanned-button:hover:not(:disabled) {
  background-color: #f5f5f5;
  border-color: #bbb;
}

.unplanned-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Meal Card Styles */
.meal-card {
  width: 100%;
  max-width: 800px;
  margin: 0 auto 20px;
  background: white;
  padding: 20px;
  border-radius: 8px;
  min-height: 200px;
  box-shadow: 0 3px 6px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.meal-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
}

.meal-card-view {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.meal-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  border-bottom: 1px solid #eee;
  padding-bottom: 15px;
}

.meal-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.meal-title h3 {
  margin: 0;
  font-size: 1.5em;
  color: #2c3e50;
}

.meal-title.no-meal h3 {
  color: #95a5a6;
  font-style: italic;
}

.meal-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.edit-button {
  display: flex;
  align-items: center;
  gap: 5px;
  background-color: #f39c12;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.edit-button:hover {
  background-color: #d68910;
}

.edit-icon {
  font-size: 1.2em;
}

.action-buttons {
  display: flex;
  gap: 8px;
}

.undo-button {
  background: none;
  border: none;
  color: #3498db;
  font-size: 1.5em;
  cursor: pointer;
  padding: 0 8px;
  transition: transform 0.2s ease;
}

.undo-button:hover {
  transform: scale(1.1);
  color: #2980b9;
}

.undo-confirmation {
  display: flex;
  align-items: center;
  gap: 8px;
  background-color: rgba(52, 152, 219, 0.1);
  padding: 4px 8px;
  border-radius: 4px;
}

.confirm-yes, .confirm-no {
  padding: 4px 8px;
  border-radius: 4px;
  border: 1px solid;
  cursor: pointer;
  font-size: 0.85em;
}

.confirm-yes {
  background-color: #3498db;
  color: white;
  border-color: #2980b9;
}

.confirm-no {
  background-color: #95a5a6;
  color: white;
  border-color: #7f8c8d;
}

.delete-button {
  background: none;
  border: none;
  color: #e74c3c;
  font-size: 1.5em;
  cursor: pointer;
  padding: 0 8px;
  transition: transform 0.2s ease;
}

.delete-button:hover {
  transform: scale(1.1);
  color: #c0392b;
}

.delete-confirmation {
  display: flex;
  align-items: center;
  gap: 8px;
  background-color: rgba(231, 76, 60, 0.1);
  padding: 4px 8px;
  border-radius: 4px;
}

.meal-card-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-top: 5px;
}

.meal-description {
  margin: 0;
  color: #666;
  line-height: 1.5;
  min-height: 30px;
}

.meal-description.empty {
  color: #95a5a6;
  font-style: italic;
}

/* Tags styling */
.meal-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin: 0.75rem 0;
}

.tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  width: 100%;
}

.tag {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.75rem;
  border-radius: 16px;
  font-size: 0.75rem;
  font-weight: 500;
  box-shadow: 0 1px 2px rgba(0,0,0,0.1);
}

/* Edit Form */
.edit-form {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
  text-align: left;
}

.form-group label {
  font-weight: 500;
  color: #2c3e50;
}

.form-group input,
.form-group textarea {
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  transition: border 0.3s ease, box-shadow 0.3s ease;
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #3498db;
  box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2);
}

.edit-actions {
  display: flex;
  gap: 10px;
  justify-content: center;
  margin-top: 10px;
}

.save-button,
.cancel-button {
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  border: 1px solid;
  font-weight: 500;
  transition: all 0.3s ease;
}

.save-button {
  background-color: #2ecc71;
  color: white;
  border-color: #27ae60;
}

.save-button:hover {
  background-color: #27ae60;
}

.cancel-button {
  background-color: #e74c3c;
  color: white;
  border-color: #c0392b;
}

.cancel-button:hover {
  background-color: #c0392b;
}

/* Meal suggestions section */
.meal-suggestions {
  width: 100%;
  max-width: 800px;
  margin: 0 auto 20px;
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 3px 6px rgba(0, 0, 0, 0.1);
}

.suggestion-actions {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 15px;
}

.suggest-button {
  background-color: #3498db;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
  font-weight: 500;
  min-width: 200px;
}

.suggest-button:hover:not(:disabled) {
  background-color: #2980b9;
}

.suggest-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.suggested-recipe {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 15px;
  background-color: #f8f9fa;
  padding: 15px;
  border-radius: 8px;
  width: 100%;
  max-width: 500px;
}

.suggested-meal-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  width: 100%;
  text-align: center;
}

.suggested-meal-info h4 {
  margin: 0;
  font-size: 1.1em;
  color: #2c3e50;
}

.suggested-meal-info p {
  margin: 0;
  font-size: 1.2em;
  font-weight: 500;
  color: #34495e;
}

.suggested-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  justify-content: center;
  margin-top: 5px;
}

.suggested-tag {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.75rem;
  border-radius: 16px;
  font-size: 0.75rem;
  font-weight: 500;
  box-shadow: 0 1px 2px rgba(0,0,0,0.1);
}

.accept-button {
  background-color: #2ecc71;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
  font-weight: 500;
  min-width: 120px;
}

.accept-button:hover {
  background-color: #27ae60;
}

/* Add styles for the meal rules section */
.meal-rules-section {
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
}

/* Notification style */
.notification {
  padding: 12px 20px;
  margin-bottom: 20px;
  border-radius: 4px;
  color: white;
  text-align: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  font-weight: 500;
}

.notification.success {
  background-color: #2ecc71;
}

.notification.info {
  background-color: #3498db;
}

.notification.error {
  background-color: #e74c3c;
}

.notification.warning {
  background-color: #f39c12;
}

/* Tag color styles */
/* Diet tags */
.tag[data-tag*="vegetarisch"], .tag[data-tag*="vegan"], .suggested-tag[data-tag*="vegetarisch"], .suggested-tag[data-tag*="vegan"] {
  background-color: #e8f5e9;
  color: #2e7d32;
}

.tag[data-tag*="glutten-free"], .tag[data-tag*="low fodmap"], .suggested-tag[data-tag*="glutten-free"], .suggested-tag[data-tag*="low fodmap"] {
  background-color: #f3e5f5;
  color: #7b1fa2;
}

/* Protein tags */
.tag[data-tag*="fish"], .tag[data-tag*="zalm"], .tag[data-tag*="tonijn"], 
.suggested-tag[data-tag*="fish"], .suggested-tag[data-tag*="zalm"], .suggested-tag[data-tag*="tonijn"] {
  background-color: #e3f2fd;
  color: #1565c0;
}

.tag[data-tag*="meat"], .tag[data-tag*="chicken"], .tag[data-tag*="beef"], .tag[data-tag*="kip"], .tag[data-tag*="gehakt"], .tag[data-tag*="varken"], .tag[data-tag*="wild"],
.suggested-tag[data-tag*="meat"], .suggested-tag[data-tag*="chicken"], .suggested-tag[data-tag*="beef"], .suggested-tag[data-tag*="kip"], .suggested-tag[data-tag*="gehakt"], .suggested-tag[data-tag*="varken"], .suggested-tag[data-tag*="wild"] {
  background-color: #fce4ec;
  color: #c2185b;
}

/* Cuisine tags */
.tag[data-tag*="asian"], .tag[data-tag*="chinese"], .tag[data-tag*="thai"], .tag[data-tag*="indian"],
.suggested-tag[data-tag*="asian"], .suggested-tag[data-tag*="chinese"], .suggested-tag[data-tag*="thai"], .suggested-tag[data-tag*="indian"] {
  background-color: #fff3e0;
  color: #e65100;
}

.tag[data-tag*="italian"], .tag[data-tag*="italiaans"], .tag[data-tag*="mediteraans"],
.suggested-tag[data-tag*="italian"], .suggested-tag[data-tag*="italiaans"], .suggested-tag[data-tag*="mediteraans"] {
  background-color: #e8eaf6;
  color: #303f9f;
}

.tag[data-tag*="mexican"], .tag[data-tag*="mexicaans"], .tag[data-tag*="spanish"], .tag[data-tag*="spaans"],
.suggested-tag[data-tag*="mexican"], .suggested-tag[data-tag*="mexicaans"], .suggested-tag[data-tag*="spanish"], .suggested-tag[data-tag*="spaans"] {
  background-color: #fff8e1;
  color: #ff6f00;
}

/* Cooking method tags */
.tag[data-tag*="bbq"], .tag[data-tag*="airfryer"],
.suggested-tag[data-tag*="bbq"], .suggested-tag[data-tag*="airfryer"] {
  background-color: #ffebee;
  color: #c62828;
}

.tag[data-tag*="lang koken"], .tag[data-tag*="ovenschotel"],
.suggested-tag[data-tag*="lang koken"], .suggested-tag[data-tag*="ovenschotel"] {
  background-color: #ede7f6;
  color: #4527a0;
}

.tag[data-tag*="takeout"], .tag[data-tag*="restaurant"],
.suggested-tag[data-tag*="takeout"], .suggested-tag[data-tag*="restaurant"] {
  background-color: #e0f2f1;
  color: #00695c;
}

.tag[data-tag*="easy"], .tag[data-tag*="quick"],
.suggested-tag[data-tag*="easy"], .suggested-tag[data-tag*="quick"] {
  background-color: #e1f5fe;
  color: #0277bd;
}

/* Carb/starch tags */
.tag[data-tag*="pasta"], .tag[data-tag*="noodles"], .tag[data-tag*="rijst"], .tag[data-tag*="rice"],
.suggested-tag[data-tag*="pasta"], .suggested-tag[data-tag*="noodles"], .suggested-tag[data-tag*="rijst"], .suggested-tag[data-tag*="rice"] {
  background-color: #f9fbe7;
  color: #827717;
}

.tag[data-tag*="aardappel"], .tag[data-tag*="potato"], .tag[data-tag*="puree"], .tag[data-tag*="friet"],
.suggested-tag[data-tag*="aardappel"], .suggested-tag[data-tag*="potato"], .suggested-tag[data-tag*="puree"], .suggested-tag[data-tag*="friet"] {
  background-color: #fff3e0;
  color: #bf360c;
}

.tag[data-tag*="brood"],
.suggested-tag[data-tag*="brood"] {
  background-color: #efebe9;
  color: #4e342e;
}

/* Vegetable tags */
.tag[data-tag*="brocolli"], .tag[data-tag*="spinazie"], .tag[data-tag*="bloemkool"], .tag[data-tag*="courgette"], .tag[data-tag*="pompoen"], .tag[data-tag*="salade"],
.suggested-tag[data-tag*="brocolli"], .suggested-tag[data-tag*="spinazie"], .suggested-tag[data-tag*="bloemkool"], .suggested-tag[data-tag*="courgette"], .suggested-tag[data-tag*="pompoen"], .suggested-tag[data-tag*="salade"] {
  background-color: #f1f8e9;
  color: #558b2f;
}

/* Other characteristics */
.tag[data-tag*="vettig"], .tag[data-tag*="comfort"],
.suggested-tag[data-tag*="vettig"], .suggested-tag[data-tag*="comfort"] {
  background-color: #fafafa;
  color: #424242;
}

/* Default style if no specific category matches */
.tag, .suggested-tag {
  background-color: #f5f5f5;
  color: #424242;
}

/* Add styles for the meal loading spinner */
.meal-loading-spinner {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100px;
  margin: 20px 0;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid rgba(52, 152, 219, 0.2);
  border-radius: 50%;
  border-top-color: #3498db;
  animation: spin 1s ease-in-out infinite;
  margin-bottom: 10px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.meal-loading-spinner p {
  color: #3498db;
  font-size: 14px;
}

/* Calendar section - keeping this the same as requested */
.calendar-container {
  width: 100%;
}

.calendar-section {
  width: 100%;
  max-width: 400px;
  margin: 0 auto;
}

/* Desktop layout */
@media (min-width: 1024px) {
  .meal-display {
    flex-direction: row;
    align-items: flex-start;
  }

  .meal-browser {
    flex: 1;
    margin-right: 2rem;
    max-width: 800px;
  }

  .calendar-container {
    width: 400px;
    position: sticky;
    top: 100px; /* Adjust based on your header height */
  }

  .calendar-section {
    margin: 0;
  }
  
  /* Special nav buttons in a row on desktop */
  .special-nav-buttons {
    flex-direction: row;
  }
}

/* Tablet layout */
@media (max-width: 1023px) and (min-width: 768px) {
  .meal-navigation {
    max-width: 90%;
  }
  
  .meal-card,
  .meal-suggestions,
  .meal-rules-section {
    max-width: 90%;
  }
}

/* Mobile layout improvements */
@media (max-width: 767px) {
  .nav-header {
    flex-direction: column;
    gap: 15px;
  }
  
  .meal-date-container {
    order: -1;
    margin-bottom: 10px;
  }
  
  .special-nav-buttons {
    flex-direction: column;
  }
  
  .meal-card-header {
    flex-direction: column;
    gap: 10px;
    align-items: center;
  }
  
  .meal-actions {
    width: 100%;
    justify-content: center;
    margin-top: 10px;
  }
}
</style>