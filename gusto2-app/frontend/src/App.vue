<template>
  <div id="app">
    <header>
      <h1>Gusto2 App</h1>
    </header>
    <main>
      <div class="card">
        <p>{{ message }}</p>
        <button @click="fetchMessage">Get Message from Backend</button>
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
      message: 'Click the button to get a message from the backend 2'
    };
  },
  methods: {
    async fetchMessage() {
      try {
        const response = await axios.get('/api/hello');
        this.message = response.data.message;
      } catch (error) {
        console.error('Error fetching message:', error);
        this.message = 'Error fetching message from backend';
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
