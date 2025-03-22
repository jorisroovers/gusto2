<template>
  <div class="tag-input">
    <div class="tags-container">
      <span v-for="tag in tags" :key="tag" class="tag" :data-tag="tag">
        {{ tag }}
        <button class="remove-tag" @click="removeTag(tag)">&times;</button>
      </span>
      <input
        ref="input"
        type="text"
        v-model="inputValue"
        @input="onInput"
        @keydown.enter.prevent="addCurrentTag"
        @keydown.backspace="handleBackspace"
        @keydown.down="selectNextSuggestion"
        @keydown.up.prevent="selectPrevSuggestion"
        @blur="onBlur"
        :placeholder="tags.length ? '' : 'Enter tags'"
      />
    </div>
    <div v-show="showSuggestions && filteredSuggestions.length" class="suggestions">
      <div
        v-for="(suggestion, index) in filteredSuggestions"
        :key="suggestion"
        class="suggestion"
        :class="{ active: index === activeSuggestionIndex }"
        :data-tag="suggestion.toLowerCase()"
        @mousedown="addTag(suggestion)"
        @mouseover="activeSuggestionIndex = index"
      >
        {{ suggestion }}
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'TagInput',
  props: {
    modelValue: {
      type: String,
      default: ''
    },
    suggestions: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      inputValue: '',
      tags: [],
      showSuggestions: false,
      activeSuggestionIndex: 0,
    }
  },
  computed: {
    filteredSuggestions() {
      const input = this.inputValue.toLowerCase()
      return this.suggestions
        .filter(s => !this.tags.includes(s)) // Exclude already selected tags
        .filter(s => s.toLowerCase().includes(input))
    }
  },
  watch: {
    modelValue: {
      immediate: true,
      handler(newValue) {
        this.tags = newValue ? newValue.split(',').map(t => t.trim()).filter(t => t) : []
      }
    }
  },
  methods: {
    updateValue() {
      this.$emit('update:modelValue', this.tags.join(', '))
    },
    addTag(tag) {
      if (tag && !this.tags.includes(tag)) {
        this.tags.push(tag)
        this.inputValue = ''
        this.updateValue()
      }
    },
    addCurrentTag() {
      if (this.showSuggestions && this.filteredSuggestions.length) {
        this.addTag(this.filteredSuggestions[this.activeSuggestionIndex])
      } else if (this.inputValue.trim()) {
        this.addTag(this.inputValue.trim())
      }
      this.showSuggestions = false
    },
    removeTag(tag) {
      const index = this.tags.indexOf(tag)
      if (index > -1) {
        this.tags.splice(index, 1)
        this.updateValue()
      }
    },
    handleBackspace(e) {
      if (!this.inputValue && this.tags.length) {
        e.preventDefault()
        this.removeTag(this.tags[this.tags.length - 1])
      }
    },
    onInput() {
      this.showSuggestions = true
      this.activeSuggestionIndex = 0
    },
    onBlur() {
      setTimeout(() => {
        this.showSuggestions = false
      }, 200)
    },
    selectNextSuggestion() {
      if (this.activeSuggestionIndex < this.filteredSuggestions.length - 1) {
        this.activeSuggestionIndex++
      }
    },
    selectPrevSuggestion() {
      if (this.activeSuggestionIndex > 0) {
        this.activeSuggestionIndex--
      }
    }
  }
}
</script>

<style scoped>
.tag-input {
  position: relative;
  width: 100%;
}

.tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 4px;
  min-height: 36px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
}

.tag {
  display: flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.875rem;
  font-weight: 500;
}

/* Tag colors for both tags and suggestions */
/* Diet tags */
.tag[data-tag*="vegetarisch"], .tag[data-tag*="vegan"],
.suggestion[data-tag*="vegetarisch"], .suggestion[data-tag*="vegan"] {
  background-color: #e8f5e9;
  color: #2e7d32;
}

.tag[data-tag*="glutten-free"], .tag[data-tag*="low fodmap"],
.suggestion[data-tag*="glutten-free"], .suggestion[data-tag*="low fodmap"] {
  background-color: #f3e5f5;
  color: #7b1fa2;
}

/* Protein tags */
.tag[data-tag*="fish"], .tag[data-tag*="zalm"], .tag[data-tag*="tonijn"],
.suggestion[data-tag*="fish"], .suggestion[data-tag*="zalm"], .suggestion[data-tag*="tonijn"] {
  background-color: #e3f2fd;
  color: #1565c0;
}

.tag[data-tag*="meat"], .tag[data-tag*="chicken"], .tag[data-tag*="beef"], .tag[data-tag*="kip"], .tag[data-tag*="gehakt"], .tag[data-tag*="varken"], .tag[data-tag*="wild"],
.suggestion[data-tag*="meat"], .suggestion[data-tag*="chicken"], .suggestion[data-tag*="beef"], .suggestion[data-tag*="kip"], .suggestion[data-tag*="gehakt"], .suggestion[data-tag*="varken"], .suggestion[data-tag*="wild"] {
  background-color: #fce4ec;
  color: #c2185b;
}

/* Cuisine tags */
.tag[data-tag*="asian"], .tag[data-tag*="chinese"], .tag[data-tag*="thai"], .tag[data-tag*="indian"],
.suggestion[data-tag*="asian"], .suggestion[data-tag*="chinese"], .suggestion[data-tag*="thai"], .suggestion[data-tag*="indian"] {
  background-color: #fff3e0;
  color: #e65100;
}

.tag[data-tag*="italian"], .tag[data-tag*="italiaans"], .tag[data-tag*="mediteraans"],
.suggestion[data-tag*="italian"], .suggestion[data-tag*="italiaans"], .suggestion[data-tag*="mediteraans"] {
  background-color: #e8eaf6;
  color: #303f9f;
}

.tag[data-tag*="mexican"], .tag[data-tag*="mexicaans"], .tag[data-tag*="spanish"], .tag[data-tag*="spaans"],
.suggestion[data-tag*="mexican"], .suggestion[data-tag*="mexicaans"], .suggestion[data-tag*="spanish"], .suggestion[data-tag*="spaans"] {
  background-color: #fff8e1;
  color: #ff6f00;
}

/* Cooking method tags */
.tag[data-tag*="bbq"], .tag[data-tag*="airfryer"],
.suggestion[data-tag*="bbq"], .suggestion[data-tag*="airfryer"] {
  background-color: #ffebee;
  color: #c62828;
}

.tag[data-tag*="lang koken"], .tag[data-tag*="ovenschotel"],
.suggestion[data-tag*="lang koken"], .suggestion[data-tag*="ovenschotel"] {
  background-color: #ede7f6;
  color: #4527a0;
}

.tag[data-tag*="takeout"], .tag[data-tag*="restaurant"],
.suggestion[data-tag*="takeout"], .suggestion[data-tag*="restaurant"] {
  background-color: #e0f2f1;
  color: #00695c;
}

.tag[data-tag*="easy"], .tag[data-tag*="quick"],
.suggestion[data-tag*="easy"], .suggestion[data-tag*="quick"] {
  background-color: #e1f5fe;
  color: #0277bd;
}

/* Carb/starch tags */
.tag[data-tag*="pasta"], .tag[data-tag*="noodles"], .tag[data-tag*="rijst"], .tag[data-tag*="rice"],
.suggestion[data-tag*="pasta"], .suggestion[data-tag*="noodles"], .suggestion[data-tag*="rijst"], .suggestion[data-tag*="rice"] {
  background-color: #f9fbe7;
  color: #827717;
}

.tag[data-tag*="aardappel"], .tag[data-tag*="potato"], .tag[data-tag*="puree"], .tag[data-tag*="friet"],
.suggestion[data-tag*="aardappel"], .suggestion[data-tag*="potato"], .suggestion[data-tag*="puree"], .suggestion[data-tag*="friet"] {
  background-color: #fff3e0;
  color: #bf360c;
}

.tag[data-tag*="brood"],
.suggestion[data-tag*="brood"] {
  background-color: #efebe9;
  color: #4e342e;
}

/* Vegetable tags */
.tag[data-tag*="brocolli"], .tag[data-tag*="spinazie"], .tag[data-tag*="bloemkool"], .tag[data-tag*="courgette"], .tag[data-tag*="pompoen"], .tag[data-tag*="salade"],
.suggestion[data-tag*="brocolli"], .suggestion[data-tag*="spinazie"], .suggestion[data-tag*="bloemkool"], .suggestion[data-tag*="courgette"], .suggestion[data-tag*="pompoen"], .suggestion[data-tag*="salade"] {
  background-color: #f1f8e9;
  color: #558b2f;
}

/* Other characteristics */
.tag[data-tag*="vettig"], .tag[data-tag*="comfort"],
.suggestion[data-tag*="vettig"], .suggestion[data-tag*="comfort"] {
  background-color: #fafafa;
  color: #424242;
}

/* Default styles */
.tag, .suggestion {
  background-color: #f5f5f5;
  color: #424242;
}

.remove-tag {
  background: none;
  border: none;
  margin-left: 4px;
  padding: 0 4px;
  cursor: pointer;
  font-size: 1rem;
  color: #666;
}

.remove-tag:hover {
  color: #e74c3c;
}

input {
  border: none;
  outline: none;
  flex: 1;
  min-width: 120px;
  padding: 4px;
  font-size: 0.875rem;
}

.suggestions {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  max-height: 200px;
  overflow-y: auto;
  background: white;
  border: 1px solid #ddd;
  border-radius: 4px;
  margin-top: 4px;
  z-index: 1000;
}

.suggestion {
  padding: 8px 12px;
  cursor: pointer;
  display: block;
  width: 100%;
  text-align: left;
}

/* Tag color system for suggestions */
.suggestion[data-tag*="vegetarian"], .suggestion[data-tag*="vegan"] {
  background-color: #e8f5e9;
  color: #2e7d32;
}

.suggestion[data-tag*="spicy"], .suggestion[data-tag*="hot"] {
  background-color: #fbe9e7;
  color: #d84315;
}

.suggestion[data-tag*="fish"], .suggestion[data-tag*="seafood"] {
  background-color: #e3f2fd;
  color: #1565c0;
}

.suggestion[data-tag*="meat"], .suggestion[data-tag*="chicken"], .suggestion[data-tag*="beef"], .suggestion[data-tag*="pork"] {
  background-color: #fce4ec;
  color: #c2185b;
}

.suggestion[data-tag*="quick"], .suggestion[data-tag*="easy"] {
  background-color: #f3e5f5;
  color: #7b1fa2;
}

.suggestion {
  /* Default suggestion style if no specific category matches */
  background-color: #f5f5f5;
  color: #424242;
}

.suggestion:hover,
.suggestion.active {
  filter: brightness(0.95);
}
</style>