<template>
  <div class="recipe-autocomplete">
    <div class="input-container">
      <input
        ref="input"
        type="text"
        v-model="inputValue"
        @input="onInput"
        @keydown.enter.prevent="selectCurrentSuggestion"
        @keydown.down="selectNextSuggestion"
        @keydown.up.prevent="selectPrevSuggestion"
        @blur="onBlur"
        :placeholder="placeholder"
        class="recipe-input"
      />
    </div>
    <div v-show="showSuggestions && filteredRecipes.length" class="suggestions">
      <div
        v-for="(recipe, index) in filteredRecipes"
        :key="recipe.Name"
        class="suggestion"
        :class="{ active: index === activeSuggestionIndex }"
        @mousedown="selectRecipe(recipe)"
        @mouseover="activeSuggestionIndex = index"
      >
        {{ recipe.Name }}
        <div v-if="recipe.Tags" class="suggestion-tags">
          <span v-for="tag in recipe.Tags.split(',')" 
                :key="tag.trim()" 
                class="suggestion-tag"
                :data-tag="tag.trim().toLowerCase()"
          >
            {{ tag.trim() }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'RecipeAutocomplete',
  props: {
    modelValue: {
      type: String,
      default: ''
    },
    placeholder: {
      type: String,
      default: 'Enter a recipe name'
    }
  },
  data() {
    return {
      inputValue: '',
      recipes: [],
      showSuggestions: false,
      activeSuggestionIndex: 0,
      loading: false
    }
  },
  computed: {
    filteredRecipes() {
      const input = this.inputValue.toLowerCase();
      if (!input) return this.recipes;
      
      return this.recipes.filter(recipe => {
        // Match on recipe name
        if (recipe.Name.toLowerCase().includes(input)) {
          return true;
        }
        
        // Match on tags
        if (recipe.Tags) {
          const tags = recipe.Tags.toLowerCase().split(',').map(tag => tag.trim());
          return tags.some(tag => tag.includes(input));
        }
        
        return false;
      });
    }
  },
  watch: {
    modelValue: {
      immediate: true,
      handler(newValue) {
        this.inputValue = newValue || '';
      }
    }
  },
  methods: {
    async fetchRecipes() {
      this.loading = true;
      try {
        const response = await axios.get('/api/recipes');
        if (response.data && response.data.recipes) {
          this.recipes = response.data.recipes;
        }
      } catch (error) {
        console.error('Error fetching recipes for autocomplete:', error);
      } finally {
        this.loading = false;
      }
    },
    onInput() {
      this.showSuggestions = true;
      this.activeSuggestionIndex = 0;
      this.$emit('update:modelValue', this.inputValue);
    },
    selectRecipe(recipe) {
      this.inputValue = recipe.Name;
      this.$emit('update:modelValue', recipe.Name);
      this.$emit('recipe-selected', recipe);
      this.showSuggestions = false;
    },
    selectCurrentSuggestion() {
      if (this.showSuggestions && this.filteredRecipes.length) {
        this.selectRecipe(this.filteredRecipes[this.activeSuggestionIndex]);
      }
    },
    onBlur() {
      setTimeout(() => {
        this.showSuggestions = false;
      }, 200);
    },
    selectNextSuggestion() {
      if (this.activeSuggestionIndex < this.filteredRecipes.length - 1) {
        this.activeSuggestionIndex++;
      }
    },
    selectPrevSuggestion() {
      if (this.activeSuggestionIndex > 0) {
        this.activeSuggestionIndex--;
      }
    }
  },
  mounted() {
    this.fetchRecipes();
  }
}
</script>

<style scoped>
.recipe-autocomplete {
  position: relative;
  width: 100%;
}

.input-container {
  width: 100%;
}

.recipe-input {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.recipe-input:focus {
  outline: none;
  border-color: #3498db;
  box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2);
}

.suggestions {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  max-height: 300px;
  overflow-y: auto;
  background: white;
  border: 1px solid #ddd;
  border-radius: 4px;
  margin-top: 4px;
  z-index: 1000;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.suggestion {
  padding: 8px 12px;
  cursor: pointer;
  border-bottom: 1px solid #eee;
}

.suggestion:last-child {
  border-bottom: none;
}

.suggestion.active,
.suggestion:hover {
  background-color: #f5f5f5;
}

.suggestion-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}

.suggestion-tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 6px;
  border-radius: 12px;
  font-size: 0.7rem;
  font-weight: 500;
}

/* Tag colors for suggestions */
.suggestion-tag[data-tag*="vegetarisch"], .suggestion-tag[data-tag*="vegan"] {
  background-color: #e8f5e9;
  color: #2e7d32;
}

.suggestion-tag[data-tag*="fish"], .suggestion-tag[data-tag*="zalm"], .suggestion-tag[data-tag*="tonijn"] {
  background-color: #e3f2fd;
  color: #1565c0;
}

.suggestion-tag[data-tag*="meat"], .suggestion-tag[data-tag*="chicken"], .suggestion-tag[data-tag*="beef"], .suggestion-tag[data-tag*="kip"] {
  background-color: #fce4ec;
  color: #c2185b;
}

.suggestion-tag {
  background-color: #f5f5f5;
  color: #424242;
}
</style>