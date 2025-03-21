<!-- CalendarPicker.vue -->
<template>
  <div class="calendar-picker">
    <div class="calendar-header">
      <button @click="previousMonth" class="nav-button">&lt;</button>
      <span class="month-display">{{ currentMonthDisplay }}</span>
      <button @click="nextMonth" class="nav-button">&gt;</button>
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
        const date = new Date(year, month, i);
        const dayOfWeek = date.getDay();
        const dateString = date.toISOString().split('T')[0].replace(/-/g, '/');
        
        days.push({
          day: i,
          isWeekend: dayOfWeek === 0 || dayOfWeek === 6,
          date: dateString,
          hasMeal: this.meals.some(meal => {
            return meal.Date === dateString && meal.Name && meal.Name.trim() !== '';
          })
        });
      }
      
      return days;
    }
  },
  methods: {
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
      return date.date === this.selectedDate;
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
  margin-bottom: 20px;
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
}

.weekend {
  background-color: #f8f9fa;
}

.empty {
  border: none;
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
}

.nav-button:hover {
  background-color: #f0f0f0;
}
</style>