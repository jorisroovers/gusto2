<template>
  <div id="app">
    <header>
      <h1>Gusto2 App</h1>
      <!-- Add save and reload buttons to the header -->
      <div class="header-buttons">
        <button 
          @click="saveAllChanges" 
          class="save-all-button" 
          :disabled="!hasChanges || loading"
          :title="!hasChanges ? 'No changes to save' : 'Save all changes'"
        >
          Save All Changes
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
    </header>
    <main>
      <div class="card">
        <!-- Notification area for saving/reloading status -->
        <div v-if="notification" class="notification" :class="notificationType">
          {{ notification }}
        </div>
        <div v-if="loading" class="loading">Loading meals...</div>
        <div v-else-if="error" class="error">{{ error }}</div>
        <div v-else-if="meals.length === 0" class="no-meals">No meals found</div>
        <div v-else class="meal-display">
          <!-- Meal information first with fixed height -->
          <div class="meal-info">
            <div v-if="!editMode">
              <div v-if="currentMeal.Name" class="meal-name">
                <h3>{{ currentMeal.Name }}</h3>
                <!-- Only show asterisk if current meal is in changedIndices -->
                <span v-if="isCurrentMealChanged" class="changed-indicator" title="This meal has unsaved changes">*</span>
              </div>
              <div v-else class="no-meal-planned">
                <h3>No meal planned</h3>
                <!-- Only show asterisk if current meal is in changedIndices -->
                <span v-if="isCurrentMealChanged" class="changed-indicator" title="This meal has unsaved changes">*</span>
              </div>
              <div class="meal-description">
                <p v-if="currentMeal.Notes">{{ currentMeal.Notes }}</p>
                <p v-else>&nbsp;</p>
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
      message: 'Loading meals from backend...',
      editMode: false,
      editedMeal: {},
      notification: '',
      notificationType: 'info',
      hasChanges: false, // Track if there are changes on the server
      changedIndices: [], // Track which specific indices have been changed
      lastViewedDate: null // Store the date of the last viewed meal
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
        const response = await axios.get('/api/hello');
        if (response.data && response.data.meals && response.data.meals.length > 0) {
          this.meals = response.data.meals;
          
          // Track if there are changes on the server
          this.hasChanges = response.data.hasChanges || false;
          
          // Store the changed indices
          this.changedIndices = response.data.changedIndices || [];
          
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
    
    // Methods for saving and reloading
    async saveAllChanges() {
      if (!this.hasChanges) return;
      
      this.loading = true;
      try {
        // Send all meals to the backend
        await axios.post('/api/meals/save', this.meals);
        
        // Reset the changes flag and changed indices
        this.hasChanges = false;
        this.changedIndices = [];
        
        // Show success notification
        this.showNotification('All changes saved successfully!', 'success');
      } catch (error) {
        console.error('Error saving all changes:', error);
        this.showNotification('Failed to save changes: ' + (error.response?.data?.detail || error.message), 'error');
      } finally {
        this.loading = false;
      }
    },
    
    async reloadMeals() {
      this.loading = true;
      
      // Store the current meal date before reloading
      const currentDate = this.currentMeal.Date ? new Date(this.currentMeal.Date) : null;
      this.lastViewedDate = currentDate;
      
      try {
        const response = await axios.get('/api/meals/reload');
        if (response.data && response.data.meals) {
          this.meals = response.data.meals;
          
          // Reset the changes flag and changed indices
          this.hasChanges = false;
          this.changedIndices = [];
          
          // Restore position to the previously viewed meal
          this.restoreMealPosition();
          
          // Show success notification
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
      // If we don't have a last viewed date, use default behavior
      if (!this.lastViewedDate || !this.meals.length) {
        this.selectTodaysMeal();
        return;
      }
      
      // Try to find the same date in the reloaded data
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
        // Found the same date, restore to this position
        this.currentIndex = lastViewedIndex;
        console.log(`Restored to previously viewed date at index ${lastViewedIndex}`);
      } else {
        // Date not found, try to find the closest date
        console.log('Previously viewed date not found, finding nearest date');
        this.findNearestDateTo(this.lastViewedDate);
      }
    },
    
    findNearestDateTo(targetDate) {
      if (!this.meals.length || !targetDate) return;
      
      let closestIndex = 0;
      let smallestDiff = Infinity;
      
      // Find the meal date closest to the target date
      this.meals.forEach((meal, index) => {
        if (!meal.Date) return;
        
        const mealDate = new Date(meal.Date);
        mealDate.setHours(0, 0, 0, 0);
        
        // Calculate absolute difference in days
        const diff = Math.abs(mealDate - targetDate);
        
        if (diff < smallestDiff) {
          smallestDiff = diff;
          closestIndex = index;
        }
      });
      
      this.currentIndex = closestIndex;
      console.log(`Found nearest date at index ${closestIndex}`);
    },
    
    showNotification(message, type = 'info') {
      this.notification = message;
      this.notificationType = type;
      
      // Auto-hide notification after 3 seconds
      setTimeout(() => {
        this.notification = '';
      }, 3000);
    },
    
    // Modified methods for editing
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
        // Send the updated meal directly to the backend
        const response = await axios.put(`/api/meal/${this.currentIndex}`, this.editedMeal);
        
        // Update local data with the edited meal
        this.meals[this.currentIndex] = { ...this.editedMeal };
        
        // Set the changes flag to true and update changed indices from server response
        this.hasChanges = true;
        this.changedIndices = response.data.changedIndices || [];
        
        // Show success message
        this.showNotification('Meal updated! Use Save All to persist to disk.', 'success');
        
        // Exit edit mode
        this.editMode = false;
        this.editedMeal = {};
      } catch (error) {
        console.error('Error saving meal:', error);
        this.showNotification('Failed to update meal', 'error');
      } finally {
        this.loading = false;
      }
    },
    
    // Existing navigation methods
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
  display: flex;
  flex-direction: column;
  align-items: center;
}

.header-buttons {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}

.card {
  max-width: 600px;
  margin: 0 auto;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
  background-color: #f9f9f9;
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

.navigation {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-top: 20px;
  padding-top: 15px;
  border-top: 1px solid #eaeaea;
}

.nav-column {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.center-column {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.date-display {
  margin: 0;
  font-weight: 500;
}

.meal-info {
  text-align: center;
  margin-bottom: 15px;
  min-height: 100px; /* Fixed minimum height to prevent layout jumps */
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.meal-name {
  position: relative;
}

.meal-name h3 {
  margin-top: 0;
  margin-bottom: 10px;
  display: inline-block;
}

.no-meal-planned {
  position: relative;
}

.no-meal-planned h3 {
  margin-top: 0;
  margin-bottom: 10px;
  color: #e74c3c;
  font-style: italic;
  display: inline-block;
}

.changed-indicator {
  color: #e74c3c;
  font-weight: bold;
  font-size: 1.2em;
  margin-left: 5px;
  vertical-align: top;
}

.meal-description {
  min-height: 40px; /* Fixed height for description area */
}

.meal-description p {
  margin: 0;
}

.meal-counter {
  font-size: 0.8em;
  color: #666;
  margin: 0;
}

/* Edit mode styles */
.edit-form {
  width: 100%;
  text-align: left;
  padding: 0 10px;
}

.form-group {
  margin-bottom: 12px;
}

.form-group label {
  display: block;
  margin-bottom: 4px;
  font-weight: 500;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.edit-actions {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin-bottom: 15px;
}

.save-all-button {
  background-color: #2ecc71;
  border: none;
  color: white;
  padding: 8px 15px;
  text-align: center;
  text-decoration: none;
  display: inline-block;
  font-size: 14px;
  cursor: pointer;
  border-radius: 4px;
  transition: background-color 0.3s;
}

.save-all-button:hover {
  background-color: #27ae60;
}

.save-all-button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.reload-button {
  background-color: #3498db;
  border: none;
  color: white;
  padding: 8px 15px;
  text-align: center;
  text-decoration: none;
  display: inline-block;
  font-size: 14px;
  cursor: pointer;
  border-radius: 4px;
  transition: background-color 0.3s;
}

.reload-button:hover {
  background-color: #2980b9;
}

.reload-button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.edit-button {
  background-color: #f39c12;
  border: none;
  color: white;
  padding: 6px 12px;
  text-align: center;
  text-decoration: none;
  display: inline-block;
  font-size: 12px;
  cursor: pointer;
  border-radius: 4px;
  transition: background-color 0.3s;
}

.edit-button:hover {
  background-color: #e67e22;
}

.save-button {
  background-color: #2ecc71;
  border: none;
  color: white;
  padding: 8px 15px;
  text-align: center;
  text-decoration: none;
  display: inline-block;
  font-size: 14px;
  cursor: pointer;
  border-radius: 4px;
  transition: background-color 0.3s;
}

.save-button:hover {
  background-color: #27ae60;
}

.cancel-button {
  background-color: #95a5a6;
  border: none;
  color: white;
  padding: 8px 15px;
  text-align: center;
  text-decoration: none;
  display: inline-block;
  font-size: 14px;
  cursor: pointer;
  border-radius: 4px;
  transition: background-color 0.3s;
}

.cancel-button:hover {
  background-color: #7f8c8d;
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
  min-width: 80px;
}

.today-button:hover {
  background-color: #2980b9;
}

.today-button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
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

.unplanned-button:disabled {
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