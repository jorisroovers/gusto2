<!-- CalendarPicker.vue -->
<template>
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
      <div class="weekday-header" v-for="day in weekDays" :key="day">{{ day }}</div>
      <div 
        v-for="(date, index) in calendarDays" 
        :key="index"
        class="calendar-day"
        :class="{
          'weekend': date.isWeekend,
          'empty': !date.day,
          'no-meal': date.day && !date.hasMeal,
          'current-day': isCurrentDay(date)
        }"
        @click="date.day && selectDate(date)"
      >
        {{ date.day }}
      </div>
    </div>
  </div>
</template>

<script>
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
    }
  },
  data() {
    return {
      weekDays: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
      currentMonth: new Date()
    };
  },
  computed: {
    currentMonthDisplay() {
      return this.currentMonth.toLocaleString('default', { month: 'long', year: 'numeric' });
    },
    calendarDays() {
      const days = [];
      const year = this.currentMonth.getFullYear();
      const month = this.currentMonth.getMonth();
      
      // Get first day of month and adjust for Monday start (0 = Monday, 6 = Sunday)
      const firstDay = new Date(year, month, 1);
      let startDay = firstDay.getDay() - 1;
      if (startDay === -1) startDay = 6; // Handle Sunday
      
      // Add empty days for padding at start
      for (let i = 0; i < startDay; i++) {
        days.push({ day: '', isWeekend: false });
      }
      
      // Get number of days in month
      const lastDay = new Date(year, month + 1, 0).getDate();
      
      // Add all days of the month
      for (let i = 1; i <= lastDay; i++) {
        // Create date at noon to avoid timezone issues
        const date = new Date(year, month, i, 12, 0, 0);
        const dayOfWeek = date.getDay();
        
        // Store the simple date string in YYYY-MM-DD format for consistency
        const dateString = this.formatDateToString(date);
        
        days.push({
          day: i,
          isWeekend: dayOfWeek === 0 || dayOfWeek === 6,
          date: dateString,
          hasMeal: this.meals.some(meal => {
            if (!meal.Date) return false;
            // Compare using our normalized date strings
            return this.formatDateToString(new Date(meal.Date)) === dateString && 
                   meal.Name && meal.Name.trim() !== '';
          })
        });
      }
      
      return days;
    }
  },
  methods: {
    // Helper method to format a date to YYYY-MM-DD consistently
    formatDateToString(date) {
      // Ensure we have a valid date
      if (!(date instanceof Date) || isNaN(date.getTime())) {
        return '';
      }
      
      const year = date.getFullYear();
      // Month is 0-based, so add 1 and pad with leading zero if needed
      const month = String(date.getMonth() + 1).padStart(2, '0');
      // Pad day with leading zero if needed
      const day = String(date.getDate()).padStart(2, '0');
      
      return `${year}-${month}-${day}`;
    },
    
    previousMonth() {
      this.currentMonth = new Date(this.currentMonth.getFullYear(), this.currentMonth.getMonth() - 1);
    },
    
    nextMonth() {
      this.currentMonth = new Date(this.currentMonth.getFullYear(), this.currentMonth.getMonth() + 1);
    },
    
    selectDate(date) {
      if (date.date) {
        this.$emit('date-selected', date.date);
      }
    },
    
    isCurrentDay(date) {
      if (!date.date || !this.selectedDate) return false;
      
      // Convert selectedDate to our consistent format for comparison
      const normalizedSelectedDate = this.formatDateToString(new Date(this.selectedDate));
      
      // Direct string comparison of normalized dates
      return date.date === normalizedSelectedDate;
    }
  }
};
</script>

<style scoped>
.calendar-picker {
  background: white;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  margin-top: 20px;
  border-top: 1px solid #eaeaea;
}

.calendar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.month-display {
  font-weight: 500;
  font-size: 1.1em;
}

.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
}

.weekday-header {
  text-align: center;
  font-weight: 500;
  color: #666;
  padding: 5px;
  font-size: 0.9em;
}

.calendar-day {
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #eee;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9em;
  transition: all 0.2s ease;
}

.calendar-day:not(.empty):hover {
  background-color: #f0f0f0;
  transform: scale(1.05);
}

.weekend {
  background-color: #f8f9fa;
}

.empty {
  border: none;
  cursor: default;
}

.no-meal {
  background-color: #ffe6e6;
}

.current-day {
  background-color: #e3f2fd;
  border-color: #2196f3;
  font-weight: bold;
}

.nav-button {
  background: transparent;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 5px 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.nav-button:hover {
  background-color: #f0f0f0;
  border-color: #aaa;
}

.icon {
  font-size: 1.2em;
  display: inline-block;
  line-height: 1;
}
</style>