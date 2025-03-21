<template>
  <div class="recipes-page">
    <div class="content-wrapper">
      <recipe-list />
    </div>
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
  width: 100%;
}

.content-wrapper {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 1rem;
}
</style>