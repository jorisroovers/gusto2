<template>
  <div class="recipes-page">
    <div class="content-wrapper">
      <div class="recipes-layout">
        <recipe-list ref="recipeList" :selectedTags="selectedTags" />
        <div class="tags-sidebar">
          <h3>Filter by Tags</h3>
          <div class="tags-list">
            <div 
              v-for="tag in availableTags" 
              :key="tag"
              :class="['filter-tag', { active: selectedTags.includes(tag) }]"
              @click="toggleTag(tag)"
            >
              {{ tag }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import RecipeList from '../components/RecipeList.vue';

export default {
  name: 'RecipesPage',
  components: {
    RecipeList
  },
  data() {
    return {
      selectedTags: [],
      availableTags: []
    };
  },
  methods: {
    toggleTag(tag) {
      const index = this.selectedTags.indexOf(tag);
      if (index === -1) {
        this.selectedTags.push(tag);
      } else {
        this.selectedTags.splice(index, 1);
      }
    },
    updateAvailableTags(tags) {
      this.availableTags = tags;
    }
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

.recipes-layout {
  display: grid;
  grid-template-columns: 1fr 250px;
  gap: 2rem;
  align-items: start;
}

.tags-sidebar {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  position: sticky;
  top: 2rem;
}

.tags-sidebar h3 {
  margin: 0 0 1rem 0;
  color: #2c3e50;
}

.tags-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.filter-tag {
  background-color: #f0f2f5;
  color: #2c3e50;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.filter-tag:hover {
  background-color: #e4e7eb;
}

.filter-tag.active {
  background-color: #3498db;
  color: white;
}

@media (max-width: 768px) {
  .recipes-layout {
    grid-template-columns: 1fr;
  }
  
  .tags-sidebar {
    position: static;
    margin-bottom: 2rem;
  }
  
  .tags-list {
    flex-direction: row;
    flex-wrap: wrap;
  }
}
</style>