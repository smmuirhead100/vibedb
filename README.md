# vibedb

VibeDB lets you throw anything into a database and it just works. You never need to run a migration again. It will be just as performant as a traditional database.

### TODO
- [x] Support Postgres
- [x] Agent-based query execution
- [x] Query caching
- [ ] Schema casting
    - [ ] Pydantic models
    - [ ] Python built-ins
- [ ] Add CLI
- [ ] Support SQLite
- [ ] Schema updates automatically posted to pypi
- [ ] Automatic query optimization
- [ ] Support multiple databases under one client (i.e. client is doing many ILIKE queries, perhaps a vector database is better)
- [ ] CI / CD pipeline
- [ ] Poor Practice Detection (N+1s, etc.)