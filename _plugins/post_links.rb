# Posts link to their own assets and other posts with root-relative paths ("/assets/...", "/17").
# Prefix those with the site's baseurl after conversion, leaving code samples untouched.
module PostLinks
  CODE = %r{(<pre[\s>].*?</pre>|<code[\s>].*?</code>)}m
  ATTR = %r{((?:src|href)=")/(?!/)|(url\(')/(?!/)}

  def self.rewrite(html, baseurl)
    return html if baseurl.to_s.empty?
    html.split(CODE).each_with_index.map do |part, i|
      i.odd? ? part : part.gsub(ATTR) { "#{Regexp.last_match(1) || Regexp.last_match(2)}#{baseurl}/" }
    end.join
  end
end

Jekyll::Hooks.register :posts, :post_convert do |doc|
  doc.content = PostLinks.rewrite(doc.content, doc.site.config["baseurl"])
end
