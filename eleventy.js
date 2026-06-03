const fs = require('fs');
const path = require('path');

module.exports = function(eleventyConfig) {
  eleventyConfig.addPassthroughCopy("admin");
  eleventyConfig.addPassthroughCopy("logo");
  eleventyConfig.addPassthroughCopy("images");
  eleventyConfig.addPassthroughCopy("google02ab5a5d1425c6ac.html");
  eleventyConfig.addWatchTarget("./shared.css");

  eleventyConfig.addGlobalData("news", () => {
    const newsFile = path.join(__dirname, "_data", "news.json");
    if (fs.existsSync(newsFile)) {
      return JSON.parse(fs.readFileSync(newsFile, "utf8"));
    }
    return { categories: {} };
  });

  eleventyConfig.addGlobalData("news_history", () => {
    const historyFile = path.join(__dirname, "_data", "news_history.json");
    if (fs.existsSync(historyFile)) {
      return JSON.parse(fs.readFileSync(historyFile, "utf8"));
    }
    return [];
  });

  return {
    dir: {
      input: ".",
      output: "_site",
      includes: "_includes",
      data: "_data"
    },
    templateFormats: ["njk", "md", "html"],
    htmlTemplateEngine: "njk",
    markdownTemplateEngine: "njk"
  };
};
