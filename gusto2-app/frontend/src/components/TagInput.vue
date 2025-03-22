<template>
  <div class="tag-input">
    <div class="tags-container">
      <span v-for="tag in tags" :key="tag" class="tag">
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
  background-color: #f0f2f5;
  color: #2c3e50;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.875rem;
  font-weight: 500;
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
}

.suggestion:hover,
.suggestion.active {
  background-color: #f5f5f5;
}
</style>