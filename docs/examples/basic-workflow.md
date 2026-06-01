# Basic Workflow Example 🚀

A complete FableFlow workflow from story idea to finished multimedia book.

## 📝 Story Concept

**Title**: "Emma's First Day at School"  
**Target Age**: 5-7 years  
**Theme**: Overcoming anxiety and making new friends  
**Educational Focus**: Social-emotional learning  

## Step 1: Author the Input Spec

FableFlow generates from a JSON **input spec** (a `FableFlowInput`) rather than a raw story file. Start by copying one of the bundled examples and editing the project metadata, characters, and story seed:

```bash
cp examples/cassie_beach_adventure_input.json examples/emma_story_input.json
```

The story seed captures the concept above - the theme of overcoming anxiety, the school setting, and the social-emotional learning focus - which the pipeline expands into a full narrative.

## Step 2: Validate the Spec

Check the spec parses into a valid `FableFlowInput` before generating:

```bash
# Validate the input spec
fable-flow validate examples/emma_story_input.json
```

## Step 3: Running FableFlow

Execute the generation pipeline:

```bash
# Install FableFlow
make install

# Generate the book and movie from the input spec
fable-flow generate examples/emma_story_input.json --output output/emma_story
```

## Step 4: AI Enhancement Process

### Text Enhancement
FableFlow improves story structure and language:

```markdown
# Emma's First Day at School

Emma's tummy danced with nervous butterflies as she gazed up at 
Sunshine Elementary School. The red brick building looked enormous, 
with colorful murals painted along its walls and children's laughter 
echoing from the playground.

"What if nobody wants to be my friend?" Emma whispered, tugging 
gently on her mom's hand.

Mom knelt down to Emma's eye level, her smile as warm as morning 
sunshine. "Sweet Emma, just be your wonderful self. You have such 
a kind heart and the most amazing giggle - I know you'll find 
friends who love those special things about you."

Emma took a deep, brave breath, squared her small shoulders, 
and stepped through the bright yellow doors of adventure...
```

### Illustration Generation
The AI creates consistent illustrations across scenes:

1. **Scene 1**: Emma and mom outside school building
2. **Scene 2**: Emma entering the classroom
3. **Scene 3**: Meeting her teacher, Mrs. Johnson
4. **Scene 4**: Finding her desk and supplies
5. **Scene 5**: Playground time and first interactions
6. **Scene 6**: Making a friend during art time
7. **Scene 7**: Lunch together with her new friend
8. **Scene 8**: Happy goodbye at the end of the day

### Audio Production
- **Narration**: Expressive voice reading
- **Character Voices**: Distinct voices for Emma, Mom, and Teacher
- **Background Music**: Gentle piano melody
- **Sound Effects**: School bell, children playing, footsteps

## Step 5: Output Formats

FableFlow writes the book artifacts and the movie into the output directory:

```
output/emma_story/
├── book_content.json       # Structured book (BookContent)
├── illustrations/          # Generated illustrations
├── *.pdf                   # Print-ready book
├── *.epub                  # E-reader compatible
└── *.mp4                   # Movie adaptation
```

## Step 6: Quality Review

### Educational Alignment Check
- ✅ Age-appropriate vocabulary and concepts
- ✅ Positive social-emotional messaging
- ✅ Relatable character and situation
- ✅ Clear problem-resolution structure

### Technical Quality Check
- ✅ Consistent character appearance across illustrations
- ✅ Clear narration
- ✅ Appropriate background music volume
- ✅ Proper formatting in all output formats

### Accessibility Check
- ✅ Alt text for all images
- ✅ Closed captions for audio
- ✅ High contrast text and backgrounds
- ✅ Screen reader compatibility

## Step 7: Educational Resources

FableFlow generates teaching materials:

### Discussion Questions
- How did Emma feel before her first day? Have you ever felt that way?
- What advice did Emma's mom give her? Was it helpful?
- What helped Emma make friends? What are good ways to make friends?
- How did Emma's feelings change throughout the day?

### Extension Activities
- **Art**: Draw a picture of your first day at school
- **Writing**: Write about a time you felt nervous but things turned out well
- **Role Play**: Practice introducing yourself to new friends
- **Social Skills**: Practice conversation starters for meeting new people

### Learning Objectives
- Identify and discuss emotions related to new experiences
- Develop strategies for managing anxiety in social situations
- Practice friendship skills and social interaction
- Build confidence in new environments

## Step 8: Publishing and Sharing

### Local Sharing
- Share the PDF version for printing
- Use the PowerPoint for classroom presentations
- Host the HTML version on your website

### FableFlow Community
- Submit to the community story library
- Share in creator showcase discussions
- Get feedback from other educators and parents

### Classroom Integration
- Align with social-emotional learning curriculum
- Use as a discussion starter for first-day jitters
- Create classroom activities based on the story themes

## 🔄 Iteration and Improvement

### Gathering Feedback
- Test with the target age group
- Get input from parents and teachers
- Monitor engagement and comprehension

### Refinement Options
- Adjust reading level based on feedback
- Modify illustrations for better representation
- Fine-tune narration pacing
- Add or modify educational components

### Re-generating After Changes
Edit the input spec and re-run the pipeline to produce an updated version:
```bash
fable-flow validate examples/emma_story_input.json
fable-flow generate examples/emma_story_input.json --output output/emma_story_v2
```

## 📊 Success Metrics

### Engagement Indicators
- **Reading Completion**: How many children finish the story
- **Re-reading Rate**: How often children return to the story
- **Discussion Participation**: Engagement with follow-up questions
- **Activity Completion**: Use of extension activities

### Educational Impact
- **Comprehension Assessment**: Understanding of story themes
- **Emotional Recognition**: Ability to identify and discuss feelings
- **Social Skill Development**: Application of friendship strategies
- **Confidence Building**: Reduced anxiety about new situations

## 🚀 Next Steps

### Creating Your Own Story
1. **Choose Your Theme**: What do you want children to learn?
2. **Write Your Draft**: Start with a simple narrative structure
3. **Configure FableFlow**: Set up your processing preferences
4. **Generate and Review**: Run the pipeline and evaluate results
5. **Refine and Improve**: Iterate based on feedback and testing

### Advanced Techniques
- **Series Development**: Create connected stories with recurring characters
- **Adaptive Content**: Customize stories for different reading levels
- **Interactive Elements**: Add choice-based story branches
- **Multimedia Integration**: Include videos, animations, or interactive games

---

## 💡 Tips for Success

### Story Development
- **Start Simple**: Begin with clear, straightforward narratives
- **Know Your Audience**: Research age-appropriate content and interests
- **Test Early**: Get feedback from children and educators throughout development

### Technical Best Practices
- **Version Control**: Track different story versions
- **Backup Everything**: Maintain copies of all source materials
- **Quality Checks**: Review all generated content before publishing
- **Accessibility First**: Design for inclusive access from the beginning

---

Ready to start your own story? See the [Quick Start Guide](../getting-started/quick-start.md).
