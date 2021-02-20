# sparqlcli

SPARQL command-line client based on [rdflib](https://github.com/RDFLib/rdflib) and [SPARQLWrapper](https://github.com/RDFLib/sparqlwrapper).

## usage

`sparqlcli endpoint`

Where `endpoint` is either a remote SPARQL endpoint URI or a local filename.

- `[-f,--format]` one of `html,hturtle,mdata,microdata,n3,nquads,nt,rdfa,rdfa1.0,rdfa1.1,trix,turtle,xml` May be used to avoid format auto-detection when `endpoint` is a local file.
- `[-r,--remote]` Force treating `endpoint` as a remote SPARQL server.
- `[-i,--interactive INTERACTIVE]` Boolean, normally auto-detected if a tty is present.
- `[-o,--output]` output format, one of `table,json,csv`, defaults to table display.

## REPL

REPL commands are only available in interactive mode.

- `.edit` open current query buffer in `$EDITOR` (defaults to `vim`)
- `.file <filename>` load and execute query from `<filename>`
- `.watch <filename>` poll `<filename>` for changes and continously execute queries