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
      <div class="main-content">
        <!-- Notification area for saving/reloading status -->
        <div v-if="notification" class="notification" :class="notificationType">
          {{ notification }}
        </div>
        <div v-if="loading" class="loading">Loading meals...</div>
        <div v-else-if="error" class="error">{{ error }}</div>
        <div v-else-if="meals.length === 0" class="no-meals">No meals found</div>
        <div v-else class="meal-display">
          <!-- Day view content -->
          <div class="day-view">
            <!-- Meal information first with fixed height -->
            <div class="meal-info">
              <div v-if="!editMode">
                <div v-if="currentMeal.Name" class="meal-name">
                  <h3>{{ currentMeal.Name }}</h3>
                  <span v-if="isCurrentMealChanged" class="changed-indicator" title="This meal has unsaved changes">*</span>
                  <div class="delete-container">
                    <button v-if="!showDeleteConfirmation" @click="showDeleteConfirmation = true" class="delete-button" title="Remove meal">×</button>
                    <div v-else class="delete-confirmation">
                      <span>Delete?</span>
                      <button @click="confirmDelete" class="confirm-yes">Yes</button>
                      <button @click="showDeleteConfirmation = false" class="confirm-no">No</button>
                    </div>
                  </div>
                </div>
                <div v-else class="no-meal-planned">
                  <h3>No meal planned</h3>
                  <span v-if="isCurrentMealChanged" class="changed-indicator" title="This meal has unsaved changes">*</span>
                </div>
                <!-- Add tags display -->
                <div v-if="currentMeal.Tags" class="meal-tags">
                  <div class="tags-container">
                    <span v-for="tag in currentMeal.Tags.split(',')" 
                          :key="tag.trim()" 
                          class="tag"
                    >
                      {{ tag.trim() }}
                    </span>
                  </div>
                </div>
                <div class="meal-description">
                  <p v-if="currentMeal.Notes">{{ currentMeal.Notes }}</p>
                  <p v-else>&nbsp;</p>
                </div>
                <!-- Add suggestion UI - now available for both empty and existing meals -->
                <div class="suggestion-actions">
                  <button @click="suggestMeal" class="suggest-button" :disabled="loading">
                    {{ suggestedMeal ? 'Suggest Another' : 'Suggest Meal' }}
                  </button>
                  <div v-if="suggestedMeal" class="suggested-recipe">
                    <p>Suggested: {{ suggestedMeal.Name }}</p>
                    <button @click="acceptSuggestion" class="accept-button">Accept</button>
                  </div>
                </div>
              </div>
              <div v-else class="edit-form">
                <div class="form-group">
                  <label for="mealName">Meal Name:</label>
                  <input 
                    id="mealName" 
                    type="text" 
                    v-model="editedMeal.Name" 
                    placeholder="Enter meal name"
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
                  <input 
                    id="mealTags" 
                    type="text" 
                    v-model="editedMeal.Tags" 
                    placeholder="Enter tags (comma separated)"
                  />
                </div>
              </div>
            </div>
            
            <!-- Edit mode actions -->
            <div v-if="editMode" class="edit-actions">
              <button @click="saveMeal" class="save-button">Save</button>
              <button @click="cancelEdit" class="cancel-button">Cancel</button>
            </div>
            
            <!-- Navigation buttons below meal info with date and counter -->
            <div class="navigation">
              <div class="nav-column">
                <button 
                  @click="previousMeal" 
                  :disabled="currentIndex <= 0 || editMode"
                  class="nav-button"
                >
                  &lt; Previous
                </button>
                <button 
                  @click="findPreviousUnplanned" 
                  class="unplanned-button"
                  :disabled="editMode"
                >
                  &lt; Previous Unplanned
                </button>
              </div>
              
              <div class="center-column">
                <p v-if="currentMeal.Date" class="date-display">{{ formatDate(currentMeal.Date) }}</p>
                <button @click="selectTodaysMeal" class="today-button" :disabled="editMode">Today</button>
                <p class="meal-counter">{{ currentIndex + 1 }} of {{ meals.length }}</p>
                <!-- Edit button -->
                <button v-if="!editMode" @click="startEdit" class="edit-button">Edit</button>
              </div>
              
              <div class="nav-column">
                <button 
                  @click="nextMeal" 
                  :disabled="currentIndex >= meals.length - 1 || editMode"
                  class="nav-button"
                >
                  Next &gt;
                </button>
                <button 
                  @click="findNextUnplanned" 
                  class="unplanned-button"
                  :disabled="editMode"
                >
                  Next Unplanned &gt;
                </button>
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

          <!-- Calendar picker moved below the meal display -->
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

export default {
  name: 'MealPlanPage',
  components: {
    CalendarPicker,
    MealPlanRules
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
            console.error('Error fetching changes:', changesError);
            this.changedIndices = [];
            this.hasChanges = false;
          }
          
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
        console.error('Error saving all changes:', error);
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
        console.error('Error reloading meals:', error);
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
        const response = await axios.put(`/api/meal/${this.currentIndex}`, this.editedMeal);
        
        this.meals[this.currentIndex] = { ...this.editedMeal };
        
        this.hasChanges = true;
        this.changedIndices = response.data.changedIndices || [];
        
        this.showNotification('Meal updated! Use Save All to persist to disk.', 'success');
        
        this.editMode = false;
        this.editedMeal = {};
      } catch (error) {
        console.error('Error saving meal:', error);
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
        const response = await axios.get('/api/recipes');
        const recipes = response.data.recipes;
        if (!recipes || recipes.length === 0) {
          this.showNotification('No meals available to suggest', 'error');
          return;
        }

        const availableMeals = recipes.filter(r => 
          !this.suggestedMeal || r.Name !== this.suggestedMeal.Name
        );

        if (availableMeals.length === 0) {
          this.suggestedMeal = recipes[Math.floor(Math.random() * recipes.length)];
        } else {
          this.suggestedMeal = availableMeals[Math.floor(Math.random() * availableMeals.length)];
        }
      } catch (error) {
        console.error('Error fetching meals:', error);
        this.showNotification('Failed to fetch meals for suggestion', 'error');
      }
    },

    async acceptSuggestion() {
      if (!this.suggestedMeal) return;

      const meal = {
        Name: this.suggestedMeal.Name,
        Tags: this.suggestedMeal.Tags,
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
          
          this.showNotification('Meal added to meal plan!', 'success');
        }
      } catch (error) {
        console.error('Error accepting suggestion:', error);
        this.showNotification('Failed to add meal to meal plan', 'error');
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
        console.error('Error deleting meal:', error);
        this.showNotification('Failed to remove meal', 'error');
      } finally {
        this.showDeleteConfirmation = false;
      }
    },
    
    // Handle rule-based meal suggestions
    async handleRuleSuggestion({ meal, index }) {
      try {
        const mealData = {
          Name: meal.name,
          Tags: meal.tags
        };
        
        const response = await axios.put(`/api/meal/${index}`, mealData);
        
        if (response.data.status === 'success') {
          this.meals[index] = {
            ...this.meals[index],
            ...mealData
          };
          
          this.changedIndices = response.data.changedIndices;
          this.hasChanges = this.changedIndices.length > 0;
          
          this.showNotification('Rule-suggested meal added to meal plan!', 'success');
        }
      } catch (error) {
        console.error('Error applying rule suggestion:', error);
        this.showNotification('Failed to add rule-suggested meal to meal plan', 'error');
      }
    }
  },
  mounted() {
    this.fetchMeals();
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

.day-view {
  flex: 1;
  min-width: 0; /* Prevent flex items from overflowing */
}

.meal-info {
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
  background: white;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  min-height: 200px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.meal-name {
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  margin-bottom: 15px;
}

.meal-name h3 {
  margin: 0;
  font-size: 1.5em;
  color: #2c3e50;
}

.changed-indicator {
  color: #e74c3c;
  margin-left: 8px;
  font-weight: bold;
  font-size: 1.2em;
}

.delete-container {
  position: absolute;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
}

.delete-button {
  background: none;
  border: none;
  color: #e74c3c;
  font-size: 1.5em;
  cursor: pointer;
  padding: 0 8px;
}

.delete-confirmation {
  display: flex;
  align-items: center;
  gap: 8px;
}

.confirm-yes, .confirm-no {
  padding: 4px 8px;
  border-radius: 4px;
  border: 1px solid;
  cursor: pointer;
}

.confirm-yes {
  background-color: #e74c3c;
  color: white;
  border-color: #c0392b;
}

.confirm-no {
  background-color: #95a5a6;
  color: white;
  border-color: #7f8c8d;
}

.meal-description {
  margin: 15px 0;
  min-height: 50px;
}

.meal-description p {
  margin: 0;
  color: #666;
  line-height: 1.4;
}

.suggestion-actions {
  margin-top: 15px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.suggest-button {
  background-color: #3498db;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
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
  gap: 8px;
}

.accept-button {
  background-color: #2ecc71;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.accept-button:hover {
  background-color: #27ae60;
}

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
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.edit-actions {
  display: flex;
  gap: 10px;
  justify-content: center;
  margin-bottom: 20px;
}

.save-button,
.cancel-button {
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  border: 1px solid;
}

.save-button {
  background-color: #2ecc71;
  color: white;
  border-color: #27ae60;
}

.cancel-button {
  background-color: #e74c3c;
  color: white;
  border-color: #c0392b;
}

.navigation {
  width: 100%;
  max-width: 800px;
  margin: 0 auto 20px;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 15px;
  align-items: center;
  margin-bottom: 20px;
  padding: 15px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.nav-column {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.nav-button,
.unplanned-button {
  width: fit-content;
  min-width: 100px;
  max-width: 200px;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  transition: all 0.3s ease;
}

.nav-button:hover:not(:disabled),
.unplanned-button:hover:not(:disabled) {
  background-color: #f5f5f5;
}

.nav-button:disabled,
.unplanned-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.center-column {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.date-display {
  font-size: 1.2em;
  font-weight: 500;
  color: #2c3e50;
  margin: 0;
}

.today-button {
  background-color: #3498db;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.today-button:hover:not(:disabled) {
  background-color: #2980b9;
}

.today-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.meal-counter {
  color: #666;
  margin: 0;
  font-size: 0.9em;
}

.edit-button {
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

.no-meal-planned {
  text-align: center;
  color: #666;
  margin: 20px 0;
  position: relative;
}

.no-meal-planned h3 {
  margin: 0;
  color: #95a5a6;
}

.calendar-container {
  width: 100%;
}

.calendar-section {
  width: 100%;
  max-width: 400px;
  margin: 0 auto;
}

/* Add styles for the meal rules section */
.meal-rules-section {
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
}

/* Notification style */
.notification {
  padding: 10px 15px;
  margin-bottom: 15px;
  border-radius: 4px;
  color: white;
  text-align: center;
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

/* Add styles for the meal tags display */
.meal-tags {
  margin: 10px 0;
  text-align: center;
}

.tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  justify-content: center;
}

.tag {
  background-color: #f0f2f5;
  color: #2c3e50;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 0.875rem;
  font-weight: 500;
}

/* Desktop layout */
@media (min-width: 1024px) {
  .meal-display {
    flex-direction: row;
    align-items: flex-start;
  }

  .day-view {
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
}
</style>