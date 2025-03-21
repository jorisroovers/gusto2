<template>
  <div id="app">
    <header>
      <h1>Gusto2 App</h1>
      <nav class="nav-links">
        <router-link to="/mealplan" class="nav-link" active-class="active">Meal Plan</router-link>
        <router-link to="/recipes" class="nav-link" active-class="active">Recipes</router-link>
      </nav>
    </header>
    <main>
      <router-view></router-view>
    </main>
  </div>
</template>

<script>
export default {
  name: 'App'
};
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #2c3e50;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  margin: 0;
}

header {
  background-color: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
  padding: 15px 20px;
  margin-bottom: 20px;
}

header h1 {
  margin: 0 0 15px 0;
  color: #2c3e50;
  font-size: 24px;
  font-weight: 600;
}

.nav-links {
  display: flex;
  gap: 10px;
  justify-content: center;
}

.nav-link {
  background-color: #fff;
  border: 1px solid #dee2e6;
  color: #495057;
  padding: 8px 16px;
  text-decoration: none;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.nav-link:hover {
  background-color: #e9ecef;
  text-decoration: none;
}

.nav-link.active {
  background-color: #3498db;
  color: white;
  border-color: #3498db;
}

main {
  flex: 1;
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

/* Common notification styles */
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

/* Loading and error states */
.loading, .error, .no-meals {
  text-align: center;
  padding: 20px;
  color: #666;
}

.error {
  color: #dc3545;
}

/* Reset some browser defaults */
* {
  box-sizing: border-box;
}

body {
  margin: 0;
  padding: 0;
}
</style>