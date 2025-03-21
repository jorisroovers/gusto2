<template>
  <div class="recipes-page">
    <recipe-list />
  </div>
</template>

<script>
import RecipeList from '../components/RecipeList.vue';

export default {
  name: 'RecipesPage',
  components: {
    RecipeList
  }
};
</script>

<style scoped>
.recipes-page {
  padding: 20px;
}
</style>