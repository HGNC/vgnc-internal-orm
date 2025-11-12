# Coverage Improvement Next Steps

## Current Status

### Coverage Analysis (13% → Target 20%+)
- **Current Coverage**: 13% (246/1832 statements)
- **Working Coverage**: ✅ Fixed coverage measurement issue
- **Well Covered**:
  - `sessions/__init__.py`: 100%
  - `sessions/factory.py`: 80%
  - `sessions/manager.py`: 44%
- **Zero Coverage**: All other modules need attention

### Immediate Actions Completed
1. ✅ **Fixed Coverage Measurement**: Updated workflow to use correct module paths
2. ✅ **Created Coverage Plan**: Detailed roadmap from 13% to 70%
3. ✅ **Set Phase 1 Target**: 20% coverage threshold in CI
4. ✅ **Added Test Structure**: Foundation tests for models, CLI, and config

## Strategic Next Steps

### Phase 1B: Target 25% Coverage (Next 1-2 weeks)

#### 1. Focus on High-Impact Modules
**Priority Modules by Lines of Code:**
1. `cli/main.py`: 443 lines → 30% coverage = +133 lines
2. `models/base.py`: 382 lines → 20% coverage = +76 lines
3. `models/orthology.py`: 177 lines → 25% coverage = +44 lines
4. `config/settings.py`: 138 lines → 50% coverage = +69 lines
5. `models/species.py`: 118 lines → 30% coverage = +35 lines

**Expected Impact**: +357 additional lines covered → ~31% total coverage

#### 2. Implementation Strategy

**A. CLI Module Quick Wins (Target 30% coverage)**
```python
# Focus on these functional areas:
- CLI argument parsing and validation
- Help text generation
- Command discovery
- Error handling for invalid commands
- Basic output formatting
```

**B. BaseModel Core Methods (Target 20% coverage)**
```python
# Focus on these high-value methods:
- to_dict() method (various options)
- to_json() method
- update_from_dict() method
- get_table_name() class method
- get_column_names() class method
- TimestampMixin.touch() method
```

**C. Configuration Validation (Target 50% coverage)**
```python
# Focus on validation paths:
- DatabaseConfig validation for all drivers
- URL construction for different databases
- SSL certificate validation
- Settings helper methods
- Environment variable parsing
```

### Phase 2: Target 40% Coverage (Weeks 3-4)

#### 1. Model Business Logic
**Target Modules:**
- `models/species.py`: Full CRUD and validation
- `models/assembly.py`: Full functionality testing
- `models/chromosomes.py`: Core business logic

#### 2. Integration Testing
- Cross-module functionality
- Database interaction patterns
- Error handling paths

## Implementation Guidelines

### 1. Test Structure Best Practices
```python
# Follow existing patterns in test_models_simple.py
class TestModuleName(BaseUnitTest, ModelTestMixin, DatabaseTestMixin):
    model_class = TargetModel
    sample_data = {...}
    required_fields = [...]

    def test_module_functionality(self):
        # Test specific module functionality
        pass
```

### 2. Focus on Business Value
- **High Priority**: Code that users interact with directly
- **Medium Priority**: Internal business logic and validation
- **Low Priority**: Edge cases and error paths (add later)

### 3. Use Existing Testing Framework
- Leverage `BaseUnitTest` for consistent test structure
- Use `DatabaseTestMixin` for database-related tests
- Follow `ModelTestMixin` patterns for model testing

## Weekly Targets

### Week 1-2: 25% Coverage
- [ ] CLI argument parsing (25% of cli/main.py)
- [ ] BaseModel utility methods (20% of models/base.py)
- [ ] Configuration validation (50% of config/settings.py)
- [ ] Remove failing tests from Phase 1 attempts

### Week 3-4: 35% Coverage
- [ ] Species model business logic
- [ ] Assembly model functionality
- [ ] CLI command execution
- [ ] Error handling improvements

### Week 5-6: 45% Coverage
- [ ] Chromosomes model testing
- [ ] CLI output formatting
- [ ] Integration tests
- [ ] Performance optimizations

## Tools and Automation

### 1. Coverage Tracking
```bash
# Daily coverage check
PYTHONPATH=src python -m pytest tests/unit/ --cov=vgnc_internal_orm --cov-report=term-missing

# Coverage breakdown by module
PYTHONPATH=src python -m pytest tests/unit/ --cov=vgnc_internal_orm --cov-report=html:htmlcov-daily
```

### 2. Coverage Gates
- **Current**: 20% minimum
- **Phase 1B**: 25% minimum
- **Phase 2**: 35% minimum
- **Phase 3**: 45% minimum
- **Target**: 70% minimum

### 3. Automated Monitoring
- Set up coverage badges in README
- Weekly coverage reports
- PR coverage change tracking

## Quality Assurance

### 1. Test Quality Metrics
- **Coverage Quality**: Ensure tests cover meaningful code paths
- **Test Performance**: Keep test suite execution under 5 minutes
- **Test Reliability**: Maintain >95% pass rate

### 2. Review Process
- Code review for new tests
- Coverage impact assessment
- Test case documentation

## Risk Mitigation

### 1. Common Challenges
- **Complex Dependencies**: Use mocking for external services
- **Database Setup**: Use SQLite in-memory for testing
- **Test Maintenance**: Keep tests focused and maintainable

### 2. Contingency Plans
- **Extended Timeline**: Adjust targets based on complexity
- **Prioritization**: Focus on business-critical functionality first
- **Tooling**: Invest in better testing tools if needed

## Success Metrics

### Coverage Targets
- ✅ **Week 2**: 25% coverage
- 🎯 **Week 4**: 35% coverage
- 🎯 **Week 6**: 45% coverage
- 🎯 **Week 8**: 55% coverage
- 🎯 **Target**: 70% coverage

### Quality Metrics
- Test pass rate: >95%
- Test execution time: <5 minutes
- Code review coverage: 100% for new tests

## Immediate Next Actions

1. **This Week**: Focus on CLI module testing (highest impact)
2. **Remove**: Failing tests that don't provide coverage
3. **Implement**: BaseModel method testing
4. **Monitor**: Daily coverage reports
5. **Adjust**: Strategy based on results

This systematic approach will ensure steady, measurable progress toward the 70% coverage target while maintaining code quality and development velocity.