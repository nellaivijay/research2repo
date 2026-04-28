# HuggingFace Space Deployment Guide

This guide explains how to deploy Research2Repo to HuggingFace Spaces for easy web access.

## Prerequisites

- HuggingFace account
- Research2Repo repository cloned locally
- Required API keys configured

## Deployment Steps

### 1. Create a New HuggingFace Space

1. Go to [HuggingFace Spaces](https://huggingface.co/spaces)
2. Click "Create new Space"
3. Choose "Gradio" as the SDK
4. Name your space (e.g., `research2repo-demo`)
5. Set it to public or private as desired
6. Click "Create Space"

### 2. Configure the Space

Copy the following files to your HuggingFace Space repository:

#### `README.md` (Space Configuration)
```yaml
---
title: Research2Repo
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 4.44.0
app_file: web/app.py
pinned: false
license: apache-2.0
---
```

#### `requirements.txt`
```
gradio>=4.44.0
torch>=2.0.0
numpy>=1.24.0
pandas>=2.0.0
matplotlib>=3.7.0
PyYAML>=6.0
```

#### `web/app.py`
Copy the entire `web/app.py` file from the Research2Repo repository.

### 3. Set Environment Variables

In your HuggingFace Space settings, add the following secrets:

- `GEMINI_API_KEY`: Your Google Gemini API key (if using Gemini)
- `OPENAI_API_KEY`: Your OpenAI API key (if using OpenAI)
- `ANTHROPIC_API_KEY`: Your Anthropic API key (if using Anthropic)

### 4. Deploy the Space

1. Push the files to your HuggingFace Space repository
2. The Space will automatically build and deploy
3. Once built, your Gradio app will be available at the Space URL

## Local Testing with HuggingFace CLI

### Install HuggingFace CLI

```bash
pip install huggingface_hub
```

### Login to HuggingFace

```bash
huggingface-cli login
```

### Test Locally

```bash
# Clone your space
git clone https://huggingface.co/spaces/your-username/research2repo-demo
cd research2repo-demo

# Copy required files
# - web/app.py
# - requirements.txt
# - README.md (with Space config)

# Test locally
gradio web/app.py
```

### Deploy to HuggingFace

```bash
git add .
git commit -m "Deploy Research2Repo to HuggingFace Space"
git push
```

## Features Available in HuggingFace Space

- **Paper Upload**: Upload PDF files or provide URLs
- **Interactive Analysis**: Analyze papers with different AI models
- **Pipeline Visualization**: See pipeline progress in real-time
- **Cost Estimation**: Estimate costs before running full pipeline
- **Provider Comparison**: Compare different AI providers
- **Model Selection**: Choose from multiple AI models

## Customization

### Adding Custom Models

Edit `web/app.py` to add custom model options:

```python
model_dropdown = gr.Dropdown(
    label="Model",
    choices=[
        "gemini-1.5-pro",
        "gpt-4o",
        "claude-3-5-sonnet",
        "your-custom-model"
    ],
    value="gemini-1.5-pro"
)
```

### Custom Styling

Modify the `custom_css` variable in `web/app.py` to customize the appearance.

### Adding New Features

The `web/app.py` file is modular - you can add new tabs and features following the existing pattern.

## Troubleshooting

### Build Failures

- Check that all dependencies are in `requirements.txt`
- Verify that `web/app.py` is properly configured
- Check the Space logs for specific error messages

### API Key Issues

- Ensure environment variables are set in Space settings
- Verify that API keys are valid and have sufficient credits
- Check that the provider names match the configuration

### Performance Issues

- Use the "minimal" pipeline configuration for faster execution
- Limit the number of concurrent users in Space settings
- Consider upgrading to a paid Space tier for better performance

## Cost Management

HuggingFace Spaces pricing:
- **CPU**: Free tier available
- **GPU**: Paid tiers starting at $0.10/hour
- **Storage**: Free tier with limited storage

To minimize costs:
- Use CPU for most operations
- Use GPU only for intensive tasks
- Clean up temporary files regularly
- Monitor API usage costs

## Security Considerations

- Never commit API keys to the repository
- Use HuggingFace Secrets for sensitive data
- Enable Space authentication if needed
- Regularly rotate API keys
- Monitor usage for unusual activity

## Alternative Deployment Options

### Docker Deployment

```bash
# Build Docker image
docker build -t research2repo .

# Run container
docker run -p 7860:7860 research2repo
```

### Streamlit Deployment

Convert the Gradio interface to Streamlit for alternative deployment.

### FastAPI Deployment

Create a REST API version for programmatic access.

## Maintenance

### Regular Updates

- Update dependencies regularly
- Monitor and apply security patches
- Update model configurations as needed
- Review and optimize performance

### Monitoring

- Monitor Space logs regularly
- Track usage statistics
- Review error logs
- Monitor API costs

### Backup and Recovery

- Regular backup of Space configuration
- Version control for all customizations
- Disaster recovery plan
- Documentation of custom modifications

## Support

For issues specific to:
- **HuggingFace Spaces**: Check [HuggingFace Documentation](https://huggingface.co/docs/hub/spaces)
- **Research2Repo**: Check [Research2Repo GitHub Issues](https://github.com/nellaivijay/Research2Repo/issues)
- **API Providers**: Check respective provider documentation

## Best Practices

1. **Start Simple**: Deploy with minimal features first, then expand
2. **Test Thoroughly**: Test locally before deploying to HuggingFace
3. **Monitor Usage**: Keep track of usage and costs
4. **Version Control**: Maintain proper versioning of deployments
5. **Documentation**: Document any custom modifications
6. **Security First**: Never expose sensitive data
7. **Performance**: Optimize for better user experience
8. **Accessibility**: Ensure the interface is accessible to all users

## Conclusion

HuggingFace Spaces provides an excellent platform for deploying Research2Repo's Gradio interface, making it accessible to a wide audience without requiring users to install dependencies or configure API keys locally.