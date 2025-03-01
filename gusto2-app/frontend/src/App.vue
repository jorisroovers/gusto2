<template>
  <div id="app">
    <header>
      <h1>Gusto2 App</h1>
    </header>
    <main>
      <div class="card">
        <p>{{ message }}</p>
        <button @click="fetchMeal">Get First Meal from Backend</button>
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
      message: 'Click the button to get a meal from the backend'
    };
  },
  methods: {
    async fetchMeal() {
      try {
        const response = await axios.get('/api/hello');
        this.message = `First Meal: ${response.data.meals[0]}`;
      } catch (error) {
        console.error('Error fetching meal:', error);
        this.message = 'Error fetching meal from backend';
      }
    }
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
}

.card {
  max-width: 500px;
  margin: 0 auto;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
  background-color: #f9f9f9;
}

button {
  background-color: #4CAF50;
  border: none;
  color: white;
  padding: 10px 20px;
  text-align: center;
  text-decoration: none;
  display: inline-block;
  font-size: 16px;
  margin: 10px 2px;
  cursor: pointer;
  border-radius: 4px;
  transition: background-color 0.3s;
}

button:hover {
  background-color: #45a049;
}
</style>
