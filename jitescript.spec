Name:		jitescript
Version:	0.4.3
Release:	1
Summary:	Java bytecode builder used by JRuby
Group:		Development/Java
License:	Apache-2.0
URL:		https://github.com/qmx/jitescript
# Tag jitescript-0.4.3. Eight Java sources. JRuby 9.4.14 asks for
# 0.4.1, which does not compile against ASM 9. 0.4.3 keeps the same
# builder API and types visibleAnnotations as List of AnnotationNode.
# The Gradle tool is not involved.
Source0:	jitescript-%{version}.tar.gz

BuildArch:	noarch
BuildRequires:	java-current-devel
BuildRequires:	sysjar
BuildRequires:	javapackages-filesystem
BuildRequires:	mvn(org.ow2.asm:asm)
BuildRequires:	mvn(org.ow2.asm:asm-tree)

%description
me.qmx.jitescript:jitescript %{version}. JiteClass.defineMethod and
toBytes emit a class file. The sources are compiled with javac
against the system ASM jars.

%prep
%autosetup -n jitescript-jitescript-%{version} -p1
find . -type f \( -name '*.jar' -o -name '*.class' -o -name '*.so' -o -name '*.node' -o -name '*.wasm' \) -print > binaries.list
find . -type d -name '*.jar' -print >> binaries.list
if [ -s binaries.list ]; then
	cat binaries.list
	exit 1
fi
find src/main/java -name '*.java' | sort > sources.list
test "$(wc -l < sources.list)" -eq 8

%build
set -eo pipefail
export JAVA_HOME=%{_jvmdir}/java-openjdk
export PATH="$JAVA_HOME/bin:$PATH"
ASM=%{_javadir}/asm.jar:%{_javadir}/asm-tree.jar
mkdir -p classes
javac --release 8 -Xlint:-options -encoding UTF-8 -cp "$ASM" -d classes @sources.list
test "$(find classes -name '*.class' | wc -l)" -eq 9
javap -v -classpath classes me.qmx.jitescript.JiteClass | grep -F -q 'major version: 52'
printf '%s\n' 'Manifest-Version: 1.0' 'Automatic-Module-Name: me.qmx.jitescript' > manifest.mf
jar cfm jitescript.jar manifest.mf -C classes .
jar i jitescript.jar
jar tf jitescript.jar | grep -F -q 'me/qmx/jitescript/JiteClass.class'
desc=$(jar --describe-module --file jitescript.jar)
printf '%s\n' "$desc"
if printf '%s\n' "$desc" | grep -F -q 'Unable'; then
	exit 1
fi
printf '%s\n' "$desc" | grep -F -q 'me.qmx.jitescript'

cat > jitescript.pom << 'END'
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>me.qmx.jitescript</groupId>
  <artifactId>jitescript</artifactId>
  <version>0.4.3</version>
  <name>jitescript</name>
  <description>Java API for bytecode.</description>
  <url>https://github.com/qmx/jitescript</url>
  <licenses>
    <license>
      <name>Apache-2.0</name>
      <url>https://www.apache.org/licenses/LICENSE-2.0.txt</url>
    </license>
  </licenses>
  <dependencies>
    <dependency>
      <groupId>org.ow2.asm</groupId>
      <artifactId>asm</artifactId>
      <version>9.11.1</version>
    </dependency>
    <dependency>
      <groupId>org.ow2.asm</groupId>
      <artifactId>asm-tree</artifactId>
      <version>9.11.1</version>
    </dependency>
  </dependencies>
</project>
END

%install
set -eo pipefail
sysjar install --buildroot %{buildroot} \
	--artifact jitescript.pom:jitescript.jar \
	--file-name jitescript \
	--filelist .mfiles
idx="%{buildroot}/usr/share/sysjar/index/me.qmx.jitescript/jitescript.sysjar"
test -s "$idx"
grep -F -q '"version": "0.4.3"' "$idx"
grep -F -q '"artifactId": "jitescript"' "$idx"
test -s %{buildroot}%{_javadir}/jitescript.jar

%check
set -eo pipefail
export JAVA_HOME=%{_jvmdir}/java-openjdk
export PATH="$JAVA_HOME/bin:$PATH"
JAR=%{buildroot}%{_javadir}/jitescript.jar
ASM=%{_javadir}/asm.jar:%{_javadir}/asm-tree.jar
test -s "$JAR"
mkdir -p check
cat > check/Smoke.java << 'EOF'
import me.qmx.jitescript.CodeBlock;
import me.qmx.jitescript.JiteClass;

import static me.qmx.jitescript.CodeBlock.newCodeBlock;
import static org.objectweb.asm.Opcodes.ACC_PUBLIC;
import static org.objectweb.asm.Opcodes.ACC_STATIC;

public class Smoke {
    static final class Loader extends ClassLoader {
        Loader() {
            super(Smoke.class.getClassLoader());
        }

        Class<?> define(byte[] bytes) {
            return defineClass("jite.Add", bytes, 0, bytes.length);
        }
    }

    public static void main(String[] args) throws Exception {
        JiteClass cls = new JiteClass("jite/Add");
        CodeBlock body = newCodeBlock().iconst_2().iconst_5().iadd().ireturn();
        cls.defineMethod("answer", ACC_PUBLIC | ACC_STATIC, "()I", body);
        byte[] bytes = cls.toBytes();
        Class<?> add = new Loader().define(bytes);
        int got = (int) add.getMethod("answer").invoke(null);
        if (got != 7) {
            throw new AssertionError(got);
        }
        System.out.println("jitescript_ok " + got);
    }
}
EOF
javac --release 8 -Xlint:-options -cp "$JAR:$ASM" -d check check/Smoke.java
"$JAVA_HOME/bin/java" -cp "check:$JAR:$ASM" Smoke > check/out.txt
cat check/out.txt
grep -F -qx 'jitescript_ok 7' check/out.txt

%files -f .mfiles
%doc README.md
%license LICENSE
