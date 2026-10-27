# Generates archive pages: /category, /category/<name>[/<sub>], /tag/<name>.
module BlogArchives
  class ArchivePage < Jekyll::Page
    def initialize(site, dir, name, data)
      @site = site
      @base = site.source
      @dir = dir
      @name = name
      process(name)
      self.content = ""
      self.data = data
    end
  end

  class Generator < Jekyll::Generator
    safe true
    priority :low

    def generate(site)
      posts = site.posts.docs.sort_by { |p| -p.date.to_i }

      site.pages << ArchivePage.new(site, "category", "index.html",
        "layout" => "archive", "archive_type" => "category", "archive_title" => "전체 글",
        "title" => "전체 글", "archive_path" => "", "list_posts" => posts)

      category_paths(site).each do |path|
        matched = posts.select { |p| (c = p.data["category"].to_s) == path || c.start_with?("#{path}/") }
        parts = path.split("/")
        site.pages << ArchivePage.new(site, File.join("category", *parts[0..-2]), "#{parts.last}.html",
          "layout" => "archive", "archive_type" => "category", "archive_title" => parts.last,
          "archive_path" => path, "title" => "#{parts.last} 카테고리", "list_posts" => matched)
      end

      tag_counts = Hash.new(0)
      posts.each { |p| Array(p.data["tags"]).each { |t| tag_counts[t] += 1 } }
      tag_counts.each_key do |tag|
        matched = posts.select { |p| Array(p.data["tags"]).include?(tag) }
        site.pages << ArchivePage.new(site, "tag", "#{tag}.html",
          "layout" => "archive", "archive_type" => "tag", "archive_title" => tag,
          "title" => "#{tag} 태그", "list_posts" => matched)
      end
      site.data["all_tags"] = tag_counts.sort_by { |t, n| [-n, t.downcase] }.map { |t, n| { "name" => t, "count" => n } }
    end

    def category_paths(site)
      Array(site.config["category_tree"]).flat_map do |c|
        [c["name"]] + Array(c["children"]).map { |ch| "#{c['name']}/#{ch}" }
      end
    end
  end
end
