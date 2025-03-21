import { createRouter, createWebHistory } from 'vue-router'
import MealPlanPage from './pages/MealPlanPage.vue'
import RecipesPage from './pages/RecipesPage.vue'

const routes = [
  {
    path: '/',
    redirect: '/mealplan'
  },
  {
    path: '/mealplan',
    name: 'MealPlan',
    component: MealPlanPage
  },
  {
    path: '/recipes',
    name: 'Recipes',
    component: RecipesPage
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router