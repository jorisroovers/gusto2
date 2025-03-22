<template>
  <div class="meal-plan-rules">
    <div class="rules-header">
      <h3>Meal Plan Rules</h3>
    </div>
    
    <div class="rule-actions">
      <button @click="validateMealPlan" class="validate-button" :disabled="loading">
        Validate Meal Plan
      </button>
      <button @click="suggestMeals" class="suggest-button" :disabled="loading">
        Get Rule-Based Suggestions
      </button>
    </div>

    <!-- Validation Results Section -->
    <div v-if="validationResults" class="validation-results">
      <div class="result-section">
        <h4>Constraints <span :class="constraintsClass">({{ constraintStatus }})</span></h4>
        <ul class="rules-list">
          <li v-for="(constraint, index) in validationResults.constraints" :key="'c-'+index" 
            :class="{'rule-valid': constraint.is_valid, 'rule-invalid': !constraint.is_valid}">
            <div class="rule-name">{{ constraint.rule_name }}</div>
            <div class="rule-message">{{ constraint.message }}</div>
          </li>
        </ul>
      </div>
      
      <div class="result-section">
        <h4>Requirements <span :class="requirementsClass">({{ requirementStatus }})</span></h4>
        <ul class="rules-list">
          <li v-for="(requirement, index) in validationResults.requirements" :key="'r-'+index"
            :class="{'rule-valid': requirement.is_valid, 'rule-invalid': !requirement.is_valid}">
            <div class="rule-name">{{ requirement.rule_name }}</div>
            <div class="rule-message">{{ requirement.message }}</div>
          </li>
        </ul>
      </div>
    </div>

    <!-- Suggestions Section -->
    <div v-if="suggestions.length > 0" class="suggestions-section">
      <h4>Rule-Based Meal Suggestions</h4>
      <div class="suggestions-list">
        <div v-for="(suggestion, index) in suggestions" :key="index" class="suggestion-item">
          <div class="suggestion-content">
            <div class="suggestion-name">{{ suggestion.meal.name }}</div>
            <div class="suggestion-tags" v-if="suggestion.meal.tags">
              Tags: {{ suggestion.meal.tags }}
            </div>
            <div class="suggestion-reasons">
              <strong>Why this meal:</strong>
              <ul>
                <li v-for="(reason, rIndex) in suggestion.reasons" :key="rIndex">
                  {{ reason }}
                </li>
              </ul>
            </div>
          </div>
          <button @click="useThisSuggestion(suggestion.meal, currentIndex)" class="use-suggestion-button">
            Use This Meal
          </button>
        </div>
      </div>
    </div>

    <!-- Error/Status messages -->
    <div v-if="error" class="error-message">{{ error }}</div>
    <div v-if="loading" class="loading-message">Loading...</div>
    
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'MealPlanRules',
  props: {
    currentDate: {
      type: String,
      default: null
    },
    currentIndex: {
      type: Number,
      default: 0
    }
  },
  data() {
    return {
      validationResults: null,
      suggestions: [],
      loading: false,
      error: null
    };
  },
  computed: {
    formattedDate() {
      if (!this.currentDate) return null;
      
      // Convert from ISO to YYYY/MM/DD format for the API
      try {
        const date = new Date(this.currentDate);
        return `${date.getFullYear()}/${String(date.getMonth() + 1).padStart(2, '0')}/${String(date.getDate()).padStart(2, '0')}`;
      } catch (e) {
        console.error('Error formatting date:', e);
        return null;
      }
    },
    
    constraintsClass() {
      if (!this.validationResults) return '';
      return this.validationResults.all_constraints_met ? 'status-success' : 'status-error';
    },
    
    requirementsClass() {
      if (!this.validationResults) return '';
      return this.validationResults.all_requirements_met ? 'status-success' : 'status-warning';
    },
    
    constraintStatus() {
      if (!this.validationResults) return '';
      return this.validationResults.all_constraints_met ? 'All Met' : 'Issues Found';
    },
    
    requirementStatus() {
      if (!this.validationResults) return '';
      return this.validationResults.all_requirements_met ? 'All Met' : 'Some Not Met';
    }
  },
  methods: {
    async validateMealPlan() {
      this.loading = true;
      this.error = null;
      this.validationResults = null;
      
      try {
        const response = await axios.post('/api/rules/validate', {
          date: this.formattedDate
        });
        
        if (response.data && response.data.status === 'success') {
          this.validationResults = response.data;
        } else {
          throw new Error('Unexpected response format');
        }
      } catch (error) {
        console.error('Error validating meal plan:', error);
        this.error = 'Failed to validate meal plan: ' + (error.response?.data?.detail || error.message);
      } finally {
        this.loading = false;
      }
    },
    
    async suggestMeals() {
      if (!this.currentDate) {
        this.error = 'No date selected for suggestions';
        return;
      }
      
      this.loading = true;
      this.error = null;
      this.suggestions = [];
      
      try {
        const response = await axios.post('/api/rules/suggest-meals', {
          date: this.formattedDate,
          count: 3
        });
        
        if (response.data && response.data.status === 'success') {
          this.suggestions = response.data.suggestions;
        } else {
          throw new Error('Unexpected response format');
        }
      } catch (error) {
        console.error('Error getting meal suggestions:', error);
        this.error = 'Failed to get meal suggestions: ' + (error.response?.data?.detail || error.message);
      } finally {
        this.loading = false;
      }
    },
    
    async useThisSuggestion(meal, index) {
      // Convert tags to lowercase before checking validations
      const mealData = {
        Name: meal.name,
        Tags: meal.tags ? meal.tags.split(',').map(t => t.trim().toLowerCase()).join(',') : ''
      };
      
      // Emit an event to let the parent component handle applying the suggestion
      this.$emit('use-suggestion', { 
        meal: mealData, 
        index: index 
      });
    }
  },
  watch: {
    currentDate() {
      // Clear previous results when date changes
      this.validationResults = null;
      this.suggestions = [];
    }
  }
};
</script>

<style scoped>
.meal-plan-rules {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  padding: 20px;
  margin-top: 20px;
}

.rules-header {
  margin-bottom: 15px;
  text-align: center;
}

.rules-header h3 {
  margin: 0;
  color: #2c3e50;
}

.rule-actions {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  justify-content: center;
}

.validate-button,
.suggest-button {
  padding: 8px 16px;
  border-radius: 4px;
  border: 1px solid;
  cursor: pointer;
  transition: all 0.3s;
}

.validate-button {
  background-color: #3498db;
  color: white;
  border-color: #2980b9;
}

.validate-button:hover:not(:disabled) {
  background-color: #2980b9;
}

.suggest-button {
  background-color: #9b59b6;
  color: white;
  border-color: #8e44ad;
}

.suggest-button:hover:not(:disabled) {
  background-color: #8e44ad;
}

.validate-button:disabled,
.suggest-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.validation-results {
  margin-top: 20px;
  display: grid;
  grid-template-columns: 1fr;
  gap: 20px;
}

@media (min-width: 768px) {
  .validation-results {
    grid-template-columns: 1fr 1fr;
  }
}

.result-section {
  background-color: #f8f9fa;
  border-radius: 6px;
  padding: 15px;
}

.result-section h4 {
  margin-top: 0;
  margin-bottom: 10px;
  color: #2c3e50;
}

.status-success {
  color: #2ecc71;
}

.status-warning {
  color: #f39c12;
}

.status-error {
  color: #e74c3c;
}

.rules-list {
  list-style-type: none;
  padding: 0;
  margin: 0;
}

.rules-list li {
  padding: 10px;
  border-radius: 4px;
  margin-bottom: 8px;
}

.rule-valid {
  background-color: rgba(46, 204, 113, 0.1);
  border-left: 3px solid #2ecc71;
}

.rule-invalid {
  background-color: rgba(231, 76, 60, 0.1);
  border-left: 3px solid #e74c3c;
}

.rule-name {
  font-weight: 500;
  margin-bottom: 5px;
}

.rule-message {
  font-size: 0.9em;
  color: #666;
}

.suggestions-section {
  margin-top: 30px;
}

.suggestions-section h4 {
  margin-top: 0;
  margin-bottom: 15px;
  color: #2c3e50;
}

.suggestions-list {
  display: grid;
  grid-template-columns: 1fr;
  gap: 15px;
}

@media (min-width: 992px) {
  .suggestions-list {
    grid-template-columns: repeat(3, 1fr);
  }
}

.suggestion-item {
  background-color: #f8f9fa;
  border-radius: 6px;
  padding: 15px;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.suggestion-content {
  flex-grow: 1;
}

.suggestion-name {
  font-weight: 500;
  font-size: 1.1em;
  margin-bottom: 8px;
  color: #2c3e50;
}

.suggestion-tags {
  font-size: 0.9em;
  color: #666;
  margin-bottom: 10px;
}

.suggestion-reasons {
  font-size: 0.9em;
  margin-bottom: 15px;
}

.suggestion-reasons ul {
  padding-left: 20px;
  margin: 5px 0 0 0;
}

.use-suggestion-button {
  margin-top: 10px;
  background-color: #2ecc71;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 8px 12px;
  cursor: pointer;
  transition: background-color 0.3s;
  align-self: flex-start;
}

.use-suggestion-button:hover {
  background-color: #27ae60;
}

.error-message {
  color: #e74c3c;
  margin-top: 15px;
  padding: 8px;
  background-color: rgba(231, 76, 60, 0.1);
  border-radius: 4px;
}

.loading-message {
  color: #3498db;
  margin-top: 15px;
  text-align: center;
}
</style>