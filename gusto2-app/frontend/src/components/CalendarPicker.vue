<!-- CalendarPicker.vue -->
<template>
  <div>
    <div class="calendar-picker">
      <div class="calendar-header">
        <button @click="previousMonth" class="nav-button">
          <span class="icon">&#x2190;</span>
        </button>
        <span class="month-display">{{ currentMonthDisplay }}</span>
        <button @click="nextMonth" class="nav-button">
          <span class="icon">&#x2192;</span>
        </button>
      </div>
      <div class="calendar-grid">
        <!-- Weekday headers including validation column -->
        <div class="weekday-header" v-for="day in [...weekDays, 'Valid']" :key="day">{{ day }}</div>
        
        <!-- Calendar rows -->
        <template v-for="week in calendarWeeks" :key="week.weekStart">
          <!-- Days of the week -->
          <template v-for="(date, index) in week.days" :key="index">
            <div 
              class="calendar-day"
              :class="{
                'weekend': date.isWeekend,
                'empty': !date.day,
                'no-meal': date.day && !date.hasMeal,
                'current-day': isCurrentDay(date),
                'changed': date.isChanged,
                'other-month': date.isOtherMonth
              }"
              @click="date.day && selectDate(date)"
            >
              <span class="day-number">{{ date.day }}</span>
              <span v-if="date.isChanged" class="changed-indicator" title="This meal has unsaved changes">*</span>
            </div>
          </template>
          <!-- Validation column -->
          <div 
            class="validation-cell"
            :class="{
              'validation-loading': weekValidations[week.weekStart]?.loading,
              'validation-success': !weekValidations[week.weekStart]?.loading && weekValidations[week.weekStart]?.results && weekValidations[week.weekStart]?.results.all_constraints_met && weekValidations[week.weekStart]?.results.all_requirements_met,
              'validation-error': !weekValidations[week.weekStart]?.loading && weekValidations[week.weekStart]?.results && (!weekValidations[week.weekStart]?.results.all_constraints_met || !weekValidations[week.weekStart]?.results.all_requirements_met)
            }"
            @click="weekValidations[week.weekStart]?.results && showValidationDialog(week)"
          >
            <template v-if="weekValidations[week.weekStart]?.loading">
              <span class="loading-spinner"></span>
            </template>
            <template v-else-if="weekValidations[week.weekStart]?.results">
              <template v-if="weekValidations[week.weekStart]?.results.all_constraints_met && weekValidations[week.weekStart]?.results.all_requirements_met">
                ✓
              </template>
              <template v-else>
                {{ countFailedValidations(weekValidations[week.weekStart]?.results) }}
              </template>
            </template>
          </div>
        </template>
      </div>
    </div>

    <!-- Validation Dialog -->
    <div v-if="showingValidationResults" class="validation-dialog">
      <div class="validation-dialog-content">
        <h3>Week Validations</h3>
        <div v-if="selectedWeekValidations" class="validation-results">
          <!-- Constraints -->
          <div class="result-section">
            <h4>Constraints 
              <span :class="selectedWeekValidations.all_constraints_met ? 'status-success' : 'status-error'">
                ({{ selectedWeekValidations.all_constraints_met ? 'All Met' : 'Issues Found' }})
              </span>
            </h4>
            <ul class="rules-list">
              <li v-for="(constraint, index) in selectedWeekValidations.constraints" 
                  :key="'c-'+index"
                  :class="{'rule-valid': constraint.is_valid, 'rule-invalid': !constraint.is_valid}">
                <div class="rule-name">{{ constraint.rule_name }}</div>
                <div class="rule-message">{{ constraint.message }}</div>
              </li>
            </ul>
          </div>

          <!-- Requirements -->
          <div class="result-section">
            <h4>Requirements 
              <span :class="selectedWeekValidations.all_requirements_met ? 'status-success' : 'status-warning'">
                ({{ selectedWeekValidations.all_requirements_met ? 'All Met' : 'Some Not Met' }})
              </span>
            </h4>
            <ul class="rules-list">
              <li v-for="(requirement, index) in selectedWeekValidations.requirements" 
                  :key="'r-'+index"
                  :class="{'rule-valid': requirement.is_valid, 'rule-invalid': !requirement.is_valid}">
                <div class="rule-name">{{ requirement.rule_name }}</div>
                <div class="rule-message">{{ requirement.message }}</div>
              </li>
            </ul>
          </div>
        </div>
        <button @click="closeValidationDialog" class="close-button">Close</button>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'CalendarPicker',
  props: {
    meals: {
      type: Array,
      required: true
    },
    selectedDate: {
      type: String,
      required: true
    },
    changedIndices: {
      type: Array,
      required: false,
      default: () => []
    }
  },
  data() {
    return {
      weekDays: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
      currentMonth: new Date(),
      showingValidationResults: false,
      selectedWeekValidations: null,
      weekValidations: {},  // Store validation state separately
    };
  },
  watch: {
    selectedDate: {
      handler(newDate) {
        if (newDate) {
          const selectedDateObj = new Date(newDate);
          // Check if the selectedDate is in a different month than currentMonth
          if (
            selectedDateObj.getMonth() !== this.currentMonth.getMonth() ||
            selectedDateObj.getFullYear() !== this.currentMonth.getFullYear()
          ) {
            // Update currentMonth to the month of the selected date
            this.currentMonth = new Date(
              selectedDateObj.getFullYear(),
              selectedDateObj.getMonth(),
              1
            );
          }
        }
      },
      immediate: true // Check when component is created
    },
    currentMonth: {
      handler() {
        this.weekValidations = {}; // Clear old validations
        this.$nextTick(() => {
          this.validateAllWeeks();
        });
      },
      immediate: true
    }
  },
  computed: {
    currentMonthDisplay() {
      return this.currentMonth.toLocaleString('default', { month: 'long', year: 'numeric' });
    },
    calendarWeeks() {
      const days = [];
      const year = this.currentMonth.getFullYear();
      const month = this.currentMonth.getMonth();
      
      // Get first day of month and adjust for Monday start
      const firstDay = new Date(year, month, 1);
      let startDay = firstDay.getDay() - 1;
      if (startDay === -1) startDay = 6;
      
      // Add empty days for padding at start
      for (let i = 0; i < startDay; i++) {
        const prevMonthDay = new Date(year, month, -i);
        days.push({
          day: prevMonthDay.getDate(),
          isWeekend: prevMonthDay.getDay() === 0 || prevMonthDay.getDay() === 6,
          date: this.formatDateToString(prevMonthDay),
          isOtherMonth: true,
          hasMeal: this.checkHasMeal(prevMonthDay)
        });
      }
      
      // Get number of days in month
      const lastDay = new Date(year, month + 1, 0).getDate();
      
      // Add all days of the month
      for (let i = 1; i <= lastDay; i++) {
        const date = new Date(year, month, i, 12, 0, 0);
        const dateString = this.formatDateToString(date);
        
        const mealIndex = this.meals.findIndex(meal => {
          if (!meal.Date) return false;
          return this.formatDateToString(new Date(meal.Date)) === dateString;
        });

        days.push({
          day: i,
          isWeekend: date.getDay() === 0 || date.getDay() === 6,
          date: dateString,
          hasMeal: this.checkHasMeal(date),
          isChanged: mealIndex !== -1 && this.changedIndices.includes(mealIndex),
          isOtherMonth: false
        });
      }

      // Add days from next month to complete the last week
      const lastDayOfMonth = new Date(year, month, lastDay);
      const lastDayWeekday = lastDayOfMonth.getDay();
      if (lastDayWeekday !== 0) { // If not Sunday, add remaining days
        for (let i = 1; i <= 7 - lastDayWeekday; i++) {
          const nextMonthDay = new Date(year, month + 1, i);
          days.push({
            day: i,
            isWeekend: nextMonthDay.getDay() === 0 || nextMonthDay.getDay() === 6,
            date: this.formatDateToString(nextMonthDay),
            isOtherMonth: true,
            hasMeal: this.checkHasMeal(nextMonthDay)
          });
        }
      }

      // Group days into weeks without validation state
      const weeks = [];
      for (let i = 0; i < days.length; i += 7) {
        const weekDays = days.slice(i, i + 7);
        const weekStart = weekDays[0].date;
        const week = {
          weekStart,
          days: weekDays,
        };
        weeks.push(week);
      }

      return weeks;
    }
  },
  methods: {
    formatDateToString(date) {
      if (!(date instanceof Date) || isNaN(date.getTime())) {
        return '';
      }
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      return `${year}-${month}-${day}`;
    },
    previousMonth() {
      this.currentMonth = new Date(this.currentMonth.getFullYear(), this.currentMonth.getMonth() - 1);
      this.validateAllWeeks();
    },
    nextMonth() {
      this.currentMonth = new Date(this.currentMonth.getFullYear(), this.currentMonth.getMonth() + 1);
      this.validateAllWeeks();
    },
    selectDate(date) {
      if (date.date) {
        const matchingMeal = this.meals.find(meal => {
          if (!meal.Date) return false;
          const mealDate = new Date(meal.Date);
          const formattedMealDate = this.formatDateToString(mealDate);
          return formattedMealDate === date.date;
        });
        if (matchingMeal && matchingMeal.Date) {
          this.$emit('date-selected', matchingMeal.Date);
        } else {
          this.$emit('date-selected', date.date);
        }
      }
    },
    isCurrentDay(date) {
      if (!date.date || !this.selectedDate) return false;
      const normalizedSelectedDate = this.formatDateToString(new Date(this.selectedDate));
      return date.date === normalizedSelectedDate;
    },
    showValidationsForWeek(week) {
      // Emit event to show validation details for the week
      this.$emit('show-week-validations', week.weekStart);
    },
    async validateWeek(week) {
      if (!week.weekStart) return;

      // Set loading state using Vue 3 reactivity
      this.weekValidations[week.weekStart] = {
        loading: true,
        error: false,
        results: null
      };

      try {
        const response = await axios.post('/api/rules/validate', {
          date: this.formatDateToAPIFormat(week.weekStart)
        });
        
        if (response.data && response.data.status === 'success') {
          this.weekValidations[week.weekStart] = {
            loading: false,
            error: false,
            results: response.data
          };
        }
      } catch (error) {
        console.error('Error validating week:', error);
        this.weekValidations[week.weekStart] = {
          loading: false,
          error: true,
          results: null
        };
      }
    },

    showValidationDialog(week) {
      const validation = this.weekValidations[week.weekStart];
      if (validation && validation.results) {
        this.selectedWeekValidations = validation.results;
        this.showingValidationResults = true;
      }
    },

    closeValidationDialog() {
      this.showingValidationResults = false;
      this.selectedWeekValidations = null;
    },

    countFailedValidations(results) {
      if (!results) return 0;
      const failedConstraints = results.constraints.filter(c => !c.is_valid).length;
      const failedRequirements = results.requirements.filter(r => !r.is_valid).length;
      return failedConstraints + failedRequirements;
    },

    formatDateToAPIFormat(dateString) {
      const date = new Date(dateString);
      return `${date.getFullYear()}/${String(date.getMonth() + 1).padStart(2, '0')}/${String(date.getDate()).padStart(2, '0')}`;
    },

    checkHasMeal(date) {
      const dateString = this.formatDateToString(date);
      return this.meals.some(meal => {
        if (!meal.Date) return false;
        return this.formatDateToString(new Date(meal.Date)) === dateString && 
               meal.Name && meal.Name.trim() !== '';
      });
    },

    validateAllWeeks() {
      // For each week in calendarWeeks, trigger validation
      this.$nextTick(() => {
        this.calendarWeeks.forEach(week => {
          this.validateWeek(week);
        });
      });
    }
  },
  mounted() {
    // Validate all weeks when component is mounted
    this.validateAllWeeks();
  }
};
</script>

<style scoped>
.calendar-picker {
  background: white;
  border-radius: 8px;
  padding: 1.25rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  width: 100%;
}

.calendar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.25rem;
}

.month-display {
  font-weight: 500;
  font-size: 1.1rem;
  color: #2c3e50;
  text-align: center;
  min-width: 140px;
}

.calendar-grid {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 4px;
  aspect-ratio: 8/6;
}

.weekday-header {
  text-align: center;
  font-weight: 500;
  color: #666;
  padding: 4px 0;
  font-size: 0.875rem;
}

.calendar-day {
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #eee;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.875rem;
  transition: all 0.2s ease;
  position: relative;
  background: white;
  padding: 4px;
}

.calendar-day:not(.empty):hover {
  background-color: #f0f0f0;
  transform: scale(1.05);
  z-index: 1;
}

.weekend {
  background-color: #f8f9fa;
}

.empty {
  border: none;
  cursor: default;
  background: transparent;
}

.no-meal {
  background-color: #ffe6e6;
}

.current-day {
  background-color: #e3f2fd;
  border: 2px solid #2196f3;
  font-weight: bold;
  color: #2196f3;
}

.nav-button {
  background: transparent;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 6px 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #2c3e50;
  min-width: 40px;
}

.nav-button:hover {
  background-color: #f0f0f0;
  border-color: #aaa;
}

.icon {
  font-size: 1.1rem;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.changed-indicator {
  color: #e74c3c;
  font-weight: bold;
  font-size: 1rem;
  position: absolute;
  top: 2px;
  right: 4px;
}

/* For mobile screens, ensure calendar stays readable */
@media (max-width: 1023px) {
  .calendar-picker {
    max-width: 400px;
    margin: 0 auto;
  }
}

.validation-cell {
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #eee;
  border-radius: 4px;
  font-size: 0.875rem;
  transition: all 0.2s ease;
  position: relative;
  cursor: pointer;
}

.validation-success {
  background-color: #e8f5e9;
  color: #2e7d32;
  border-color: #a5d6a7;
}

.validation-error {
  background-color: #ffebee;
  color: #c62828;
  border-color: #ef9a9a;
}

.validation-cell:hover {
  transform: scale(1.05);
  z-index: 1;
}

.other-month {
  opacity: 0.5;
}

.validation-dialog {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.validation-dialog-content {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  max-width: 600px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}

.close-button {
  margin-top: 1rem;
  padding: 0.5rem 1rem;
  background: #e0e0e0;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.close-button:hover {
  background: #d0d0d0;
}

.validation-loading {
  background-color: #f5f5f5;
}

.loading-spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid #f3f3f3;
  border-top: 2px solid #3498db;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
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
</style>