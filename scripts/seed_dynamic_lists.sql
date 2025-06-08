-- Seed script for initial dynamic lists and items
INSERT OR
IGNORE INTO dynamic_lists (list_name)
VALUES
    ('story_genres');
INSERT OR
IGNORE INTO dynamic_lists (list_name)
VALUES
    ('image_styles_app');
INSERT OR
IGNORE INTO dynamic_lists (list_name)
VALUES
    ('writing_styles');
INSERT OR
IGNORE INTO dynamic_lists (list_name)
VALUES
    ('word_to_picture_ratio');
INSERT OR
IGNORE INTO dynamic_lists (list_name)
VALUES
    ('text_density');
INSERT OR
IGNORE INTO dynamic_lists (list_name)
VALUES
    ('openai_image_style_mappings');

INSERT OR
IGNORE INTO dynamic_list_items (list_name, item_value, item_label, is_active, sort_order)
VALUES
    -- Genres (match StoryGenre enum values exactly)
    ('story_genres', 'Children''s', 'Children’s', 1, 1),
    ('story_genres', 'Sci-Fi', 'Sci-Fi', 1, 2),
    ('story_genres', 'Drama', 'Drama', 1, 3),
    ('story_genres', 'Horror', 'Horror', 1, 4),
    ('story_genres', 'Action', 'Action', 1, 5),
    ('story_genres', 'Fantasy', 'Fantasy', 1, 6),
    ('story_genres', 'Mystery', 'Mystery', 1, 7),
    ('story_genres', 'Romance', 'Romance', 1, 8),
    ('story_genres', 'Thriller', 'Thriller', 1, 9),
    ('story_genres', 'Comedy', 'Comedy', 1, 10),
    -- Image Styles (match ImageStyle enum values exactly)
    ('image_styles_app', 'Default', 'Default', 1, 1),
    ('image_styles_app', 'Cartoon', 'Cartoon', 1, 2),
    ('image_styles_app', 'Watercolor', 'Watercolor', 1, 3),
    ('image_styles_app', 'Photorealistic', 'Photorealistic', 1, 4),
    ('image_styles_app', 'Pixel Art', 'Pixel Art', 1, 5),
    ('image_styles_app', 'Fantasy Art', 'Fantasy Art', 1, 6),
    ('image_styles_app', 'Sci-Fi Concept Art', 'Sci-Fi Concept Art', 1, 7),
    ('image_styles_app', 'Anime', 'Anime', 1, 8),
    ('image_styles_app', 'Vintage Comic Book Art', 'Vintage Comic Book Art', 1, 9),
    ('image_styles_app', 'Minimalist', 'Minimalist', 1, 10),
    ('image_styles_app', 'Noir', 'Noir', 1, 11),
    -- Word-to-Picture Ratio (match WordToPictureRatio enum values exactly)
    ('word_to_picture_ratio', 'One image per page', 'One image per page', 1, 1),
    ('word_to_picture_ratio', 'One image per two pages', 'One image per two pages', 1, 2),
    ('word_to_picture_ratio', 'One image per paragraph', 'One image per paragraph', 1, 3),
    -- Text Density (match TextDensity enum values exactly)
    ('text_density', 'Concise (~30-50 words)', 'Concise (~30-50 words)', 1, 1),
    ('text_density', 'Standard (~60-90 words)', 'Standard (~60-90 words)', 1, 2),
    ('text_density', 'Detailed (~100-150 words)', 'Detailed (~100-150 words)', 1, 3),
    -- OpenAI Image Style Mappings (uncomment and adjust as needed)
    ('openai_image_style_mappings', 'Cartoon', 'vivid', 1, 1),
    ('openai_image_style_mappings', 'Photorealistic', 'natural', 1, 2),
    ('openai_image_style_mappings', 'Watercolor', 'vivid', 1, 3);
